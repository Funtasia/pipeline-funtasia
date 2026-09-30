import functools
from signal import raise_signal
from rich.live import Live
from rich.progress import TextColumn, BarColumn, TimeElapsedColumn, Progress
from rich.console import Console
from collections.abc import AsyncIterable
from enum import Enum
from pathlib import Path
from urllib.parse import urlencode, urlunsplit, parse_qs, urlparse

import re
import time
import io
import zipfile
import asyncio
import httpx

from ..config import load_config

class Method(Enum):
    GET = "get"
    POST = "post"
    

async def make_request(
    client: httpx.AsyncClient, 
    url: httpx.URL | str, 
    method: Method, 
    /, 
    timeout: int = 120, 
    content: AsyncIterable[bytes] | bytes | str | None = None
) -> httpx._models.Response:
    """
    Make a request for `url` using `client` based on `method`.

    `content` will be sent only when Method.POST
    """
    match method:
        case Method.GET:
            response = await client.get(
                url,
                timeout=timeout
            )
        case Method.POST:
            response = await client.post(
                url,
                timeout=timeout,
                content=content
            )

    response.raise_for_status()
    return response 

    
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

def notNone(message: str | None = None, Error_class: Exception = NotImplementedError):
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

    config = load_config()

    FUNTASIA_ROOT = Path(config["dir"]["root"])

    blender_executable = Path(config["convert"]["blender_exe"])

    script_path = FUNTASIA_ROOT / config["convert"]["blender_script"]

    skp_folder = FUNTASIA_ROOT / config["convert"]["skp_folder"]

    glb_folder = FUNTASIA_ROOT / config["convert"]["glb_folder"]

    blend_folder = FUNTASIA_ROOT / config["convert"]["blend_folder"]

    skp_semaphore = asyncio.Semaphore(3)

    blender_semaphore = asyncio.Semaphore(1)

    NO_OF_ATTEMPTS = config["convert"]["attempts"]

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
        then try to use skp_folder / filename / filename.skp 
        (filename should not have file extention)

        If override (default True), replace existing files and folders.

        `client` needs to be an OPEN httpx.AsyncClient instance.

        For reporting progress, use `progress_bar` and update the task for each step.
        Multiple ConvertSkp can use the same progress bar as a new task is added for each instance.

        All other output will go to `console`, which defaults to Console().
        """
        
        if isinstance(source,Path):
            filename = source.stem
        else:
            filename = source
        
        # Defines the path to the .skp file
        if isinstance(source, Path) and source.is_file():
            self.filepath = source

        else:        

            self.filepath = ConvertSkp.skp_folder / filename / f"{filename}.skp"
            
            if not self.filepath.is_file():
                raise FileNotFoundError(f"Provided filepath - {source} is not a valid filepath")


        # Defines the directory & path as to the saving of the .blend file
        if blend_save_folder is not None:
            blend_save_folder = blend_save_folder / filename
        else:
            blend_save_folder = ConvertSkp.blend_folder / filename

        blend_save_folder.mkdir(
            parents = True,
            exist_ok=True
        )

        self.blend_save_path = blend_save_folder / f"{filename}.blend"

        # Defines the path to save the .glb
        self.glb_save_folder = glb_save_folder or ConvertSkp.glb_folder 

        self.glb_save_folder.mkdir(
            parents = True,
            exist_ok = True
        )

        self.glb_save_path = glb_save_folder / f"{filename}.glb"

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
            
        response = await make_request(
            self.client,
            "https://3dencoder.com/SKP-to-blend",
            Method.GET,
            timeout = 10
        )
    
        html = response.text
    
        m = re.search(
            r'uploadURL\s*:\s*"([^"]+)"',
            html
        ).group(1)     
    
        upload_params = parse_qs(
            urlparse(m).query
        )
    
        s = upload_params.get("s", [None])[0]
        j = upload_params.get("j", [None])[0]
        cuid = upload_params.get("cuid", [None])[0]
        
        return s, j, cuid

    @notNone(message="Did not get token (token is None)")
    async def get_token(self, s, cuid) -> str:
    
        tk_params = {
            "Method": "tk",
            "cuid": cuid,
            "s":s
        } | self.file_params
    
        token_url = urlunsplit((
            "https",
            "e1.3dwhere.com",
            "/eupload.ashx",
            urlencode(tk_params),
            ""
        ))
    
        self.console.print(f"TokenUrl: {token_url}\n")

        response = await make_request(
            self.client,
            token_url,
            Method.GET,
            timeout=50
        )

        response = response.json()
        token = response.get("token")

        self.console.print(f"Token: {token}")
    
        return token

    @notNone(message="Did not get fcode (fcode is None)")
    async def get_fcode(self, token, s, j, cuid) -> str:
        """
        Uploads .skp model file and obtains a code: 'fcode' which is subsequently used 
        to obtain the link to download the zip file
        """
    
        upload_params = {
            "Method": "upload",
            "token": token,
            "client": "html5",
            "percen": 10,
            "s": s,
            "j": j,
            "cuid": cuid
        } | self.file_params
    
        upload_url = urlunsplit((
            "https",
            "e1.3dwhere.com",
            "/eupload.ashx",
            urlencode(upload_params),
            ""
        ))
    
        self.console.print("Upload:", upload_url, "\n")

        f = self.filepath.open("rb")
        data = f.read()
        f.close()

        response = await make_request(
            self.client,
            upload_url,
            Method.POST,
            timeout = 240,
            content = data
        )

        response = response.json()
        fcode = response.get("message")
    
        return fcode

    @notNone(message="Request timed out without getting zipurl", Error_class=TimeoutError)
    async def get_zip_download_url(self, fcode: str) -> str:
        """
        Using the 'fcode' returned by 'get_fcode()', it obtains the download link for
        the zip file
        """
    
        zipurl_params = {
            "action": "getinfo",
            "fcode": fcode
        }
    
        zipurl_url = urlunsplit((
            "https",
            "e1.3dwhere.com",
            "/json.aspx",
            urlencode(zipurl_params),
            ""
        ))
    
        zipurl = None
        
        start = time.monotonic()
    
        # server sometimes responds OK, but actually still converting
        # thus keep trying with 2s interval until zipurl appears
        while zipurl is None:

            response = await make_request(
                self.client,
                zipurl_url,
                Method.POST,
                timeout = 10
            )

            response = response.json()
            zipurl = response.get("zipfile")
    
            if time.monotonic() - start > 120:
                break
    
            await asyncio.sleep(2)
    
        return zipurl
    
    async def save_zipfile(self, zipurl: str) -> None:
        """
        Using the download link returned by 'get_zip_download_url()', it saves both the
        zip file and the .blend file.
        """

        response = await make_request(
            self.client,
            zipurl,
            Method.GET,
            timeout=240
        )
    
        self.zip_save_path.write_bytes(response.content)
    
        with zipfile.ZipFile(io.BytesIO(response.content)) as z:
    
            file = z.namelist()[0]
            data = z.read(file)
            self.blend_save_path.write_bytes(data)
    

    async def upload(self) -> str:
        "Upload file and return fcode"
        s, j, cuid = await self.get_env()

        token = await self.get_token(s, cuid)

        fcode = await self.get_fcode(
            token,
            s,
            j,
            cuid
        )

        return fcode
            
        
    async def run_blender(self) -> bool:
        "Run blender and raise RuntimeError is failure"

        self.update_progress(f"[bold blue]Waiting for Blender: {self.blend_save_path.name}[/bold blue]")

        async with self.blender_semaphore:

            self.update_progress(f"[bold blue]Converting with Blender: {self.blend_save_path.name}[/bold blue]", advance=1)

            command = [
                str(self.blender_executable),
                "--background",
                str(self.blend_save_path),
                "--python",
                str(self.script_path),
            ]

            if self.glb_save_folder is not None:
                command += ["--", "--glb", str(self.glb_save_folder)]

            self.console.print(f"Starting Blender: {self.blend_save_path}")

            process = await asyncio.create_subprocess_exec(
                *command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
            )

            stdout, _ = await process.communicate()
            output = stdout.decode(errors="replace")

            if process.returncode != 0:
                self.console.print(
                    f"[red]Blender failed for {self.blend_save_path}",
                    f"(exit code {process.returncode})[/]"
                )
                raise RuntimeError(f"Blender failed with exit code {process.returncode}")

            self.console.print(f"[green]Blender completed: {self.blend_save_path}[/]")


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

            for attempt in range(ConvertSkp.NO_OF_ATTEMPTS):
                try:
                    fcode = await self.upload()
                    zipurl = await self.get_zip_download_url(fcode)
                    break

                except Exception as e:
                    self.console.print(
                        f"[red]Failed to get {self.filepath.name}:[/red]",
                        f"[blue]{type(e).__name__}[/blue]: {e}",
                        f"[yellow](attempt {attempt+1}/{ConvertSkp.NO_OF_ATTEMPTS})[/yellow]"
                    )

                    # attempt is 0-indexed
                    if attempt + 1 == ConvertSkp.NO_OF_ATTEMPTS:
                        raise

            self.update_progress(f"[bold cyan]Downloading converted zip: {self.filepath.name}[/bold cyan]", advance=1)

            await self.save_zipfile(zipurl)

            self.console.print(f"[green]{self.filepath.name} converted to .blend successfully[/]")

        await self.run_blender()
        
        self.update_progress(f"[bold green]✓ Done: {self.filepath.name}[/bold green]", advance=1)


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
    asyncio.run(main())