import asyncio
import functools
import io
import logging
import random
import time
import zipfile
from collections.abc import AsyncIterable
from enum import Enum
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urljoin, urlparse, urlsplit, urlunsplit

import httpx
from httpx._transports import base
from rich.console import Console
from rich.live import Live
from rich.logging import RichHandler
from rich.progress import BarColumn, Progress, TextColumn, TimeElapsedColumn

from ..config import Config, load_config


# httpcore and httpx will spam a lot to the terminal otherwise
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(10 + logging.getLogger().level)

logger = logging.getLogger(__name__)

class Method(Enum):
    GET = "get"
    POST = "post"
    
class aobject(object):
    """
    Generic object with async __init__

    See: https://stackoverflow.com/a/45364670
    """
    async def __new__(cls, *a, **kw):
        instance = super().__new__(cls)
        await instance.__init__(*a, **kw)
        return instance

    async def __init__(self):
        pass

def notNone(message: str | None = None, Error_class: type[Exception] = NotImplementedError):
    "Ensure the return value is not None, else raise NotImplementedError"
    
    def wrapper(f):

        @functools.wraps(f)
        def wrapped(*args, **kwargs):
            result = f(*args, **kwargs)
            if result is None:
                raise Error_class(message or f"{f.__name__} returned None")
            return result
        
        return wrapped
    
    if callable(message): # decorator used without calling
        return wrapper(message)
    
    return wrapper

class ConvertSkp(aobject):
    """
    Class to convert .skp -> .blend -> .glb.

    Example code:
    
    >>> async with httpx.AsyncClient as client:
    >>>     # since __new__ and __init__ are async, it is important 
    >>>     # to call `await` on instance creation
    >>>     conv = await ConvertSkp("model.skp", client=client)
    >>>     await conv.convert()
    """

    config: Config

    skp_semaphore = asyncio.Semaphore(3)
    blender_semaphore = asyncio.Semaphore(1)

    async def __init__(
        self, 
        source: Path | str,
        client: httpx.AsyncClient,
        glb_save_folder: Path | None = None,
        blend_save_folder: Path | None = None,
        override: bool = True,
        progress_bar: Progress | None = None,
        console: Console | None = None
    ):
        """
        If `source` is not a Path, it is treated as the filename,
        then try to use skp_folder / filename / filename.skp.
        If `source` is a Path but the file does not exist, 
        find the file using method above using its filename.
        (filename should not have file extention)

        If override (default True), replace existing files and folders.

        `client` needs to be an OPEN httpx.AsyncClient instance.

        For reporting progress, use `progress_bar` and update the task for each step.
        Multiple ConvertSkp can use the same progress bar as a new task is added for each instance.

        All other output will go to `console`, which defaults to Console().
        """

        # load config only on instance creation
        self.config = load_config()
        
        if isinstance(source,Path):
            filename = source.stem
        else:
            filename = source
        
        # Defines the path to the .skp file
        if isinstance(source, Path) and source.is_file():
            self.filepath = source

        else:        

            self.filepath = self.config.skp_folder / filename / f"{filename}.skp"
            
            if not self.filepath.is_file():
                raise FileNotFoundError(f"Provided filepath - {source} is not a valid filepath")


        # Defines the directory & path as to the saving of the .blend file
        if blend_save_folder is not None:
            blend_save_folder = blend_save_folder / filename
        else:
            blend_save_folder = self.config.blend_folder / filename

        blend_save_folder.mkdir(
            parents = True,
            exist_ok=True
        )

        self.blend_save_path = blend_save_folder / f"{filename}.blend"

        # Defines the path to save the .glb
        self.glb_save_folder = glb_save_folder or self.config.glb_folder 

        self.glb_save_folder.mkdir(
            parents = True,
            exist_ok = True
        )

        self.glb_save_path = self.glb_save_folder / f"{filename}.glb"

        self.zip_save_path = self.blend_save_path.with_suffix(".zip")

        if not override and (
            self.zip_save_path.is_file() or
            self.blend_save_path.is_file()
        ):
            raise FileExistsError("Zip/Blender file exists for model already")
        
        self.file_params = {
            "name": self.filepath.name,
            "size": self.filepath.stat().st_size
        }

        self.client = client

        # Output related
        self.console = console or Console()
        self.progress_bar = progress_bar
        if self.progress_bar:
            self.task_id = self.progress_bar.add_task(f"{self.filepath.name}", total=3, start=False)


    def update_progress(self, description, advance: float = 0):
        if self.progress_bar and self.task_id is not None:
            self.progress_bar.update(
                self.task_id, 
                description=description,
                advance=advance
            )


    async def get_env(self) -> tuple[str, str, str]:
        """
        Return a tuple of `tkurl`, `upurl`, `surl` 

        Refer to the original js at https://www.3dwhere.com/conv/model-to-blend
        """

        # cuid is 16-byte hex string (32 chars) that represents a fingerprint from FingerprintJS (from a hash function)
        # by randomly generating a new one, we get around rate limits (and also no way to check real fingerprint)
        cuid = random.randbytes(16).hex()
        logger.debug(f"cuid: {cuid}")

        response = await self.client.get(
            "https://api.3dwhere.com/account/url/convupload", 
            params={'cuid': cuid},
            timeout=10
        )
        
        result: dict = response.raise_for_status().json()
        tkurl = result.get('tkurl', '')
        upurl = result.get('upurl', '')
        surl = result.get('surl', '')
    
        if response.status_code != 200 or not all((tkurl, upurl, surl)):
            raise NotImplementedError(f"Error getting tkurl, upurl, surl: {result.get('message', '')}")

        logger.debug(f"tkurl: {tkurl}")
        logger.debug(f"upurl: {upurl}")
        logger.debug(f"surl: {surl}")

        return tkurl, upurl, surl

    @staticmethod
    def f_get_random():
        # source: https://www.3dwhere.com/loong/js/supload/js/stream-v1.js
        # used to add a dummy get param???
        return str(time.time_ns() // 1_000_000)[8:]

    @staticmethod
    def f_add_vars(json: dict, url):
        parts = urlsplit(url) 
        new_query = parse_qs(parts.query) | json
        return str(urlunsplit(parts._replace(query=urlencode(new_query,doseq=True))))

    @notNone(message="Did not get token (token is None)")
    async def get_token(self, tkurl) -> str:

        response = await self.client.get(
            f"{self.f_add_vars(self.file_params, tkurl)}&{self.f_get_random()}",
            timeout = 20
        )

        response = response.raise_for_status().json()
        token = response.get("token")

        logger.debug(f"Token: {token}")
    
        return token

    @notNone(message="Did not get fcode (fcode is None)")
    async def get_fcode(self, upurl, token) -> str:
        """
        Uploads .skp model file and obtains a code: 'fcode' which is subsequently used 
        to obtain the link to download the zip file
        """
    
        upload_params = {
            "Method": "upload",
            "to": "blend",
            "percen": 10,
            "token": token,
        } | self.file_params | {self.f_get_random(): ''}

        url = self.f_add_vars(upload_params, upurl)
    
        with self.filepath.open("rb") as f:
            data = f.read()

        logger.debug(f"Loaded '{self.filepath}', preparing to upload")

        # for some reason the original site also did a get request on the upload endpoint
        # no idea why
        upload_get = await self.client.get(
            url,
            timeout = 120
        )

        logger.debug(f"upload_get: {upload_get.json()}")

        response = await self.client.post(
            url,
            timeout = 120,
            content = data
        )

        response = response.raise_for_status().json()
        fcode = response.get("message")
    
        return fcode

    @notNone(message="Request timed out without getting zipurl", Error_class=TimeoutError)
    async def get_zip_download_url(self, base_url, fcode: str) -> str:
        """
        Using the 'fcode' returned by 'get_fcode()', it obtains the download link for
        the zip file
        """
        
        zipurl = None
        
        start = time.monotonic()
    
        # server sometimes responds OK, but actually still converting
        # thus keep trying with 2s interval until zipurl appears
        while zipurl is None:

            response = await self.client.get(
                urljoin(base_url, '/jsonconv.aspx'),
                params = {
                    "action": "getinfo",
                    "fcode": fcode
                },
                timeout = 10
            )

            response = response.raise_for_status().json()
            logger.debug(f"zipurl request: {response}")
            zipurl = response.get("zipfile")
    
            if time.monotonic() - start > 120:
                break
    
            await asyncio.sleep(3)
    
        return zipurl
    
    async def save_zipfile(self, zipurl: str) -> None:
        """
        Using the download link returned by 'get_zip_download_url()', it saves both the
        zip file and the .blend file.
        """

        response = await self.client.get(
            zipurl,
            timeout=240
        )
    
        self.zip_save_path.write_bytes(response.raise_for_status().content)
    
        with zipfile.ZipFile(io.BytesIO(response.content)) as z:
    
            file = z.namelist()[0]
            data = z.read(file)
            self.blend_save_path.write_bytes(data)
        
    async def run_blender(self):
        "Run blender and raise RuntimeError is failure"

        self.update_progress(f"[bold blue]Waiting for Blender: {self.blend_save_path.name}[/bold blue]")

        async with self.blender_semaphore:

            self.update_progress(f"[bold blue]Converting with Blender: {self.blend_save_path.name}[/bold blue]", advance=1)

            command = [
                str(self.config.blender_exe),
                "--background",
                str(self.blend_save_path),
                "--python",
                str(self.config.blender_script),
            ]

            if self.glb_save_folder is not None:
                command += ["--", "--glb", str(self.glb_save_folder)]

            logger.info(f"Starting Blender: {self.blend_save_path}")

            process = await asyncio.create_subprocess_exec(
                *command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
            )

            stdout, _ = await process.communicate()
            output = stdout.decode(errors="replace")

            if process.returncode != 0:
                logger.error(
                    f"[red]Blender failed for {self.blend_save_path} (exit code {process.returncode})[/]"
                )
                raise RuntimeError(f"Blender failed with exit code {process.returncode}")

            logger.info(f"Blender completed: {self.blend_save_path}")


    async def _convert(self):
        """
        Convert the file fully from .skp to .glb.

        All error handling is done in `convert`
        """
        self.update_progress(f"[bold yellow]Waiting for upload: {self.filepath.name}[/bold yellow]")

        async with self.skp_semaphore:
            if self.progress_bar:
                self.progress_bar.start_task(self.task_id)

            self.update_progress(f"[bold cyan]Uploading for conversion: {self.filepath.name}[/bold cyan]")

            for attempt in range(self.config.attempts):
                try:
                    # main logic code
                    tkurl, upurl, surl = await self.get_env()
                    token = await self.get_token(tkurl)
                    fcode = await self.get_fcode(upurl, token)
                    logger.info(f"Got token and fcode for {self.filepath.name}")
                    zipurl = await self.get_zip_download_url(surl, fcode)
                    logger.info(f"Got download link for {self.filepath.name}")
                    
                    # no errors
                    break

                except Exception as e:
                    logger.warning(f"Convert {self.filepath.name} failed: {type(e).__name__}: {e} (attempt {attempt+1}/{self.config.attempts})")

                    # attempt is 0-indexed
                    if attempt + 1 == self.config.attempts:
                        raise

            self.update_progress(f"[bold cyan]Downloading converted zip: {self.filepath.name}[/bold cyan]", advance=1)

            await self.save_zipfile(zipurl) #type: ignore (zipurl will always be bound, last attempt will raise)

        logger.info(f"Converted {self.filepath.name} -> {self.blend_save_path.name}")

        await self.run_blender()

        logger.info(f"Converted {self.blend_save_path.name} {self.filepath.name} (done)")
        
        self.update_progress(f"[bold green]✓ Done: {self.filepath.name} -> {self.glb_save_path.name}[/bold green]", advance=1)


    async def convert(self, suppress_errors=False) -> bool:
        """
        Convert the file in `self.filepath` (.skp) -> .blend -> .glb

        Error messages will appear in `progress_bar` if set.

        If suppress_errors=False, raise any errors that occur,
        else return False

        If conversion is successful, return True.
        """
        try:
            await self._convert()
            return True
        
        except Exception as e:
            if self.progress_bar:
                self.update_progress(f"[red]✗ Failed: {self.filepath.name} ({type(e).__name__}: {e})")
                self.progress_bar.stop_task(self.task_id)

            logger.error(f"Conversion of '{self.filepath.name}' failed: ({type(e).__name__}: {e}")

            if not suppress_errors:
                raise RuntimeError("Conversion of model failed") from e

            return False


async def main(): 
    conversion_progress = Progress(
        TextColumn("[bold blue]{task.description}"),
        BarColumn(bar_width=80),
        TextColumn("({task.completed}/{task.total})"),
        TimeElapsedColumn(),
        expand=True
    )


    with Live(conversion_progress) as l:

        async with httpx.AsyncClient() as client:

            instance = await ConvertSkp( #type: ignore
                "njc-l2-hall", 
                client,
                # glb_save_folder=Path(r"C:\Users\Gareth\docs\school\non-academics\funtasia\pipeline-funtasia"),
                glb_save_folder=Path("reallytesting"),
                blend_save_folder=Path("/tmp/blender"),
                progress_bar=conversion_progress,
                console=l.console
            )

            await instance.convert()



if __name__ == "__main__":
    logging.basicConfig(format="%(message)s", level=logging.NOTSET, handlers=[RichHandler()])
    logging.getLogger("httpcore").setLevel(logging.WARN)
    asyncio.run(main())