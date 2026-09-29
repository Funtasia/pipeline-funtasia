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

class ConvertSkp(aobject):

    config = load_config()

    FUNTASIA_ROOT = Path(config["dir"]["root"])

    blender_executable = Path(config["convert"]["blender_exe"])

    script_path = FUNTASIA_ROOT / config["convert"]["blender_script"]

    skp_folder = FUNTASIA_ROOT / config["convert"]["skp_folder"]

    blend_folder = FUNTASIA_ROOT / config["convert"]["blend_folder"]

    skp_semaphore = asyncio.Semaphore(3)

    blender_semaphore = asyncio.Semaphore(1)

    NO_OF_ATTEMPTS = config["convert"]["attempts"]

    async def __init__(
        self, 
        filename: str,
        filepath: Path | None = None ,
        blend_save_folder: Path | None = None,
        glb_save_folder: Path | None = None,
        override: bool = True,
        progress_bar: Progress | None = None,
        console: Console | None = None
    ):
        """
        If `filepath` is not provided, look in skp_folder / filename / filename.skp 
        (filename should not have file extention)

        If override (default True), replace existing files and folders.

        For reporting progress, use `progress_bar` and update the task for each step.
        Multiple ConvertSkp can use the same progress bar as a new task is added for each instance.

        All other output will go to `console`, which defaults to Console().
        """

        if not (filename or filepath):
            raise TypeError("Missing argument `filename` or `filepath`")

        self.filepath = filepath or (ConvertSkp.skp_folder / filename / filename).with_suffix(".skp")

        self.blend_save_path = (blend_save_folder or ConvertSkp.blend_folder / self.filepath.parent) / self.filepath.stem
        self.blend_save_path.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        self.glb_save_folder  = glb_save_folder
        if self.glb_save_folder is not None:
            self.glb_save_folder.parent.mkdir(
                parents=True,
                exist_ok=True
            )

        self.zip_path = self.blend_save_path.with_suffix(".zip")
        self.blend_path = self.blend_save_path.with_suffix(".blend")

        if override:
            self.zip_path.unlink(missing_ok=True)
            self.blend_path.unlink(missing_ok=True)
        
        self.file_params = {
            "name": self.filepath.name,
            "size": self.filepath.stat().st_size
        }

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


    async def get_env(self, client) -> tuple[str, str, str]:
            
        response = await make_request(
            client,
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
    
    async def get_token(self, client: httpx.AsyncClient, s, cuid) -> str:
    
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
            client,
            token_url,
            Method.GET,
            timeout=50
        )

        response = response.json()
        token = response.get("token")

        self.console.print(f"Token: {token}")

        if token is None:
            raise NotImplementedError("Did not get token (token is None)")
    
        return token

    async def get_fcode(self, client, token, s, j, cuid) -> str:
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
            client,
            upload_url,
            Method.POST,
            timeout = 240,
            content = data
        )

        response = response.json()
        fcode = response.get("message")
    
        return fcode

    async def get_zip_download_url(self, client: httpx.AsyncClient, fcode: str) -> str:
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
    
        while zipurl is None:

            response = await make_request(
                client,
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
    
    async def save_zipfile(self, client: httpx.AsyncClient, zipurl: str) -> None:
        """
        Using the download link returned by 'get_zip_download_url()', it saves both the
        zip file and the .blend file.
        """

        response = await make_request(
            client,
            zipurl,
            Method.GET,
            timeout=240
        )

    
        self.zip_path.write_bytes(response.content)
    
        with zipfile.ZipFile(io.BytesIO(response.content)) as z:
    
            file = z.namelist()[0]
            data = z.read(file)
            self.blend_path.write_bytes(data)
    

    async def _convert(self, client: httpx.AsyncClient):
        s, j, cuid = await self.get_env(client)

        token = await self.get_token(client, s, cuid)

        fcode = await self.get_fcode(
            client,
            token,
            s,
            j,
            cuid
        )

        if fcode is None:
            raise NotImplementedError("Missing fcode")

        zipurl = await self.get_zip_download_url(
            client,
            fcode
        )

        if zipurl is None:
            raise NotImplementedError("Missing zipurl")

        return zipurl
            
        
    async def run_blender(self):

        self.update_progress(f"[bold blue]Waiting for Blender: {self.blend_path.name}[/bold blue]")

        async with self.blender_semaphore:

            self.update_progress(f"[bold blue]Converting with Blender: {self.blend_path.name}[/bold blue]", advance=1)

            command = [
                str(self.blender_executable),
                "--background",
                str(self.blend_path),
                "--python",
                str(self.script_path),
            ]

            if self.glb_save_folder is not None:
                command += ["--", "--glb", str(self.glb_save_folder)]

            self.console.print(f"Starting Blender: {self.blend_path}")

            process = await asyncio.create_subprocess_exec(
                *command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
            )

            stdout, _ = await process.communicate()
            output = stdout.decode(errors="replace")

            if process.returncode != 0:
                self.console.print(
                    f"[red]Blender failed for {self.blend_path} "
                    f"(exit code {process.returncode})[/]"
                )
                return False

            self.console.print(f"[green]Blender completed: {self.blend_path}[/]")
            return True


    async def convert(self):
        self.update_progress(f"[bold yellow]Waiting for upload: {self.filepath.name}[/bold yellow]")

        async with httpx.AsyncClient() as client, self.skp_semaphore:
            if self.progress_bar:
                self.progress_bar.start_task(self.task_id)

            self.update_progress(f"[bold cyan]Uploading for conversion: {self.filepath.name}[/bold cyan]")

            for attempt in range(ConvertSkp.NO_OF_ATTEMPTS):
                try:
                    zipurl = await self._convert(client)
                    break

                except Exception as e:
                    self.console.print(f"[red]Failed to get {self.filepath.name} (attempt {attempt+1})[/]")
                    
                    self.console.print(f"Attempt {attempt+1} failed: {e}")

                    # attempt is 0-indexed
                    if attempt + 1 == ConvertSkp.NO_OF_ATTEMPTS:
                        raise

            self.update_progress(f"[bold cyan]Downloading converted zip: {self.filepath.name}[/bold cyan]", advance=1)

            await self.save_zipfile(client, zipurl)

            self.console.print(f"[green]{self.filepath.name} converted to .blend successfully[/]")

        await self.run_blender()
        
        self.update_progress(f"[bold green]✓ {self.filepath.name} done![/bold green]", advance=1)


async def main(): 
    conversion_progress = Progress(
        TextColumn("[bold blue]{task.description}"),
        BarColumn(),
        TextColumn("({task.completed}/{task.total})"),
        TimeElapsedColumn(),
    )

    with Live(conversion_progress) as l:

        instance = await ConvertSkp( #type: ignore
            "njc-l2-hall", 
            # glb_save_folder=Path(r"C:\Users\Gareth\docs\school\non-academics\funtasia\pipeline-funtasia"),
            glb_save_folder=Path("reallytesting"),
            blend_save_folder=Path("/tmp/blender"),
            progress_bar=conversion_progress,
            console=l.console
        )

        await instance.convert()



if __name__ == "__main__":
    asyncio.run(main())