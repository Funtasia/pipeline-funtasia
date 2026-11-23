import asyncio
import functools
import io
import logging
import random
import time
import zipfile
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urljoin, urlsplit, urlunsplit

import httpx
from rich.live import Live
from rich.logging import RichHandler
from rich.progress import BarColumn, Progress, TextColumn, TimeElapsedColumn

from ..config import load_config

# httpcore and httpx will spam a lot to the terminal otherwise
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(10 + logging.getLogger().level)

logger = logging.getLogger(__name__)


class aobject(object):  # noqa: UP004
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


def notNone(
    message: str | None = None, Error_class: type[Exception] = NotImplementedError
):
    "Ensure the return value is not None, else raise NotImplementedError"

    def wrapper(f):

        @functools.wraps(f)
        def wrapped(*args, **kwargs):
            result = f(*args, **kwargs)
            if result is None:
                raise Error_class(message or f"{f.__name__} returned None")
            return result

        return wrapped

    if callable(message):  # decorator used without calling
        return wrapper(message)

    return wrapper


def get_filepath_from_name(stem: str, suffix: str, directory: Path):
    if (filepath := directory / stem / (stem + suffix)).is_file() or (
        filepath := directory / (stem + suffix)
    ).is_file():
        return filepath
    else:
        try:
            return next(directory.rglob(stem + suffix))

        except StopIteration:
            raise FileNotFoundError(
                f"Cannot find file {stem + suffix} in {directory}."
            ) from None


class ConvertSkp(aobject):
    """
    Class to convert .skp -> .blend -> .glb.

    Example code:

    >>> async with httpx.AsyncClient as client:
    >>> # since __new__ and __init__ are async, it is important
    >>> # to call `await` on instance creation
    >>>     conv = await ConvertSkp("model.skp", client=client)
    >>>     await conv.convert()

    __init__ params:

    `config` is a dictionary of configuration values found in
    nipple_config.ini under the model_convert section.

    If `source` is a Path, use that as the file to convert.
    If `source` is a str, it is treated as the filename,
    then try the following locations in order:
    - skp_folder / filename / filename.skp
    - skp_folder / filename.skp
    - skp_folder / ** / filename.skp (get any match)

    If override (default True), replace existing files and folders.

    `client` is an OPEN httpx.AsyncClient instance.

    For reporting progress, use `progress_bar` and update the task for each step.
    Multiple ConvertSkp can use the same progress bar
    as a new task is added for each instance.
    """

    skp_semaphore = asyncio.Semaphore(3)
    blender_semaphore = asyncio.Semaphore(1)

    client: httpx.AsyncClient

    filepath: Path
    filename: str
    file_params: dict[str, str | int]

    blend_save_path: Path
    zip_save_path: Path
    glb_save_path: Path
    override: bool

    progress_bar: Progress | None

    async def __init__(
        self,
        source: Path | str,
        client: httpx.AsyncClient,
        config: dict[str, str] | None = None,
        override: bool = True,
        progress_bar: Progress | None = None,
    ):

        self.config: dict[str, str] = dict(
            load_config(force_default=True)["model_convert"]
        )
        self.config |= config or {}

        logger.debug(f"Got config: {self.config}")

        # Get self.filepath and self.filename
        if isinstance(source, Path):
            self.filename = source.stem
            self.filepath = source
        else:
            self.filename = source.removesuffix(".skp")
            self.filepath = get_filepath_from_name(
                self.filename, ".skp", Path(self.config["skp_folder"])
            )

        if not self.filepath.is_file():
            raise FileNotFoundError(f"Provided filepath '{source}' does not exist")

        # Get self.blend_save_path
        blend_save_folder = Path(self.config["blend_folder"]) / self.filename
        blend_save_folder.mkdir(parents=True, exist_ok=True)
        self.blend_save_path = blend_save_folder / f"{self.filename}.blend"

        # Get self.zip_save_path
        self.zip_save_path = self.blend_save_path.with_suffix(".zip")

        # Get self.glb_save_path
        glb_save_folder = Path(self.config["glb_folder"])
        glb_save_folder.mkdir(parents=True, exist_ok=True)
        self.glb_save_path = glb_save_folder / f"{self.filename}.glb"

        # Check presence of files
        if not override:
            for file in (self.blend_save_path, self.zip_save_path, self.glb_save_path):
                if file.exists():
                    raise FileExistsError(f"{file} already exists")

        self.file_params = {
            "name": self.filename,
            "size": self.filepath.stat().st_size,
        }

        self.client = client

        self.progress_bar = progress_bar
        if self.progress_bar:
            self.task_id = self.progress_bar.add_task(
                f"{self.filename}", total=3, start=False
            )

    def update_progress(self, description, advance: float = 0):
        if self.progress_bar and self.task_id is not None:
            self.progress_bar.update(
                self.task_id, description=description, advance=advance
            )

    # 3dwhere.com conversion workflow:
    #
    # 1. Generate cuid from random bytes
    # 2. Get tkurl, upurl, surl from the cuid
    # 3. Get token from tkurl (uses file params)
    # 4. Get fcode after uploading the file using upurl and token (uses file params)
    # 5. Get zip download url from surl and fcode
    # 6. Download zip file and extract the blend file
    #
    # For documentation, refer to the original js at
    # https://www.3dwhere.com/conv/model-to-blend
    # https://www.3dwhere.com/loong/js/supload/js/stream-v1.js

    @staticmethod
    def f_get_random():
        # source: https://www.3dwhere.com/loong/js/supload/js/stream-v1.js
        # used to add a dummy get param???
        return str(time.time_ns() // 1_000_000)[8:]

    @staticmethod
    def f_add_vars(json: dict, url):
        parts = urlsplit(url)
        new_query = parse_qs(parts.query) | json
        return str(urlunsplit(parts._replace(query=urlencode(new_query, doseq=True))))

    async def get_env(self) -> tuple[str, str, str]:
        """
        Return a tuple of `tkurl`, `upurl`, `surl`
        """

        # cuid is 16-byte hex string (32 chars) that represents
        # a fingerprint from FingerprintJS (from a hash function).
        # By randomly generating a new one, we get around rate
        # limits (and also no way to check real fingerprint).
        cuid = random.randbytes(16).hex()
        logger.debug(f"cuid: {cuid}")

        response = await self.client.get(
            "https://api.3dwhere.com/account/url/convupload",
            params={"cuid": cuid},
            timeout=10,
        )

        result: dict = response.raise_for_status().json()
        tkurl = result.get("tkurl", "")
        upurl = result.get("upurl", "")
        surl = result.get("surl", "")

        if response.status_code != 200 or not all((tkurl, upurl, surl)):
            raise NotImplementedError(
                f"Error getting tkurl, upurl, surl: {result.get('message', '')}"
            )

        logger.debug(f"tkurl: {tkurl}")
        logger.debug(f"upurl: {upurl}")
        logger.debug(f"surl: {surl}")

        return tkurl, upurl, surl

    @notNone(message="Did not get token (token is None)")
    async def get_token(self, tkurl) -> str:
        """
        Get token from tkurl.
        """

        response = await self.client.get(
            f"{self.f_add_vars(self.file_params, tkurl)}&{self.f_get_random()}",
            timeout=20,
        )

        response = response.raise_for_status().json()
        token = response.get("token")

        logger.debug(f"Token: {token}")

        return token

    @notNone(message="Did not get fcode (fcode is None)")
    async def get_fcode(self, upurl, token) -> str:
        """
        Upload .skp model file and return fcode.
        """

        upload_params = (
            {
                "Method": "upload",
                "to": "blend",
                "percen": 10,
                "token": token,
            }
            | self.file_params
            | {self.f_get_random(): ""}
        )

        url = self.f_add_vars(upload_params, upurl)

        with self.filepath.open("rb") as f:
            data = f.read()

        logger.debug(f"Loaded '{self.filepath}', preparing to upload")

        # for some reason original site also did a GET request on the upload endpoint
        # no idea why
        upload_get = await self.client.get(url, timeout=120)
        logger.debug(f"upload_GET: {upload_get.json()}")

        response = await self.client.post(url, timeout=120, content=data)
        response = response.raise_for_status().json()
        fcode = response.get("message")

        return fcode

    @notNone(
        message="Request timed out without getting zipurl", Error_class=TimeoutError
    )
    async def get_zip_download_url(self, base_url, fcode: str) -> str:
        """
        Get download link for the zip file using fcode.
        """

        zipurl = None
        start = time.monotonic()

        # server sometimes responds OK, but actually still converting
        # thus keep trying with 3s interval until zipurl appears
        while zipurl is None and time.monotonic() - start > 120:
            response = await self.client.get(
                urljoin(base_url, "/jsonconv.aspx"),
                params={"action": "getinfo", "fcode": fcode},
                timeout=10,
            )

            response = response.raise_for_status().json()
            logger.debug(f"zipurl request: {response}")
            zipurl = response.get("zipfile")

            await asyncio.sleep(3)

        return zipurl

    async def save_zipfile(self, zipurl: str) -> None:
        """
        Save the zip file and from zipurl and extract the blend file.
        """

        response = await self.client.get(zipurl, timeout=240)
        self.zip_save_path.write_bytes(response.raise_for_status().content)

        with zipfile.ZipFile(io.BytesIO(response.content)) as z:
            file = z.namelist()[0]
            data = z.read(file)
            self.blend_save_path.write_bytes(data)

    async def convert_skp_to_blend(self):
        """
        Fully convert skp file to blend file.

        Suppress errors until self.config["upload_attempts"] reached.
        """

        self.update_progress(f"[bold cyan]Uploading for conversion: {self.filename}[/]")

        for attempt in range(1, int(self.config["upload_attempts"]) + 1):
            try:
                tkurl, upurl, surl = await self.get_env()
                token = await self.get_token(tkurl)
                fcode = await self.get_fcode(upurl, token)
                logger.info(f"Got token and fcode for {self.filename}")
                zipurl = await self.get_zip_download_url(surl, fcode)
                logger.info(f"Got download link for {self.filename}")

                # no errors
                break

            # usually ConnectionTimeout, but can be other errors as well
            except Exception as e:
                logger.warning(
                    f"Convert {self.filename} failed: "
                    f"{type(e).__name__}: {e} "
                    f"(attempt {attempt}/{self.config['upload_attempts']})"
                )

                if attempt == int(self.config["upload_attempts"]):
                    raise

        self.update_progress(
            f"[bold cyan]Downloading converted zip: {self.filename}[/]",
            advance=1,
        )

        # (zipurl will always be bound, last attempt will raise)
        await self.save_zipfile(zipurl)

    async def convert_blend_to_glb(self):
        """
        Fully convert blend file to glb file.

        Raise RuntimeError if conversion failed.
        """

        self.update_progress(
            f"[bold blue]Converting with Blender: {self.blend_save_path.name}[/]",
            advance=1,
        )

        command = [
            str(self.config["blender_exe"]),
            "--background",
            str(self.blend_save_path),
            "--python",
            str(self.config["blender_script"]),
        ]

        command += ["--", "--glb", str(self.glb_save_path.parent)]

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
                f"Blender failed for {self.blend_save_path} "
                f"(exit code {process.returncode})"
            )
            logger.debug(output)
            raise RuntimeError(f"Blender failed with exit code {process.returncode}")

        logger.info(f"Blender completed: {self.blend_save_path}")

    async def _convert(self):
        """
        Convert the file fully from .skp to .glb.

        Use `.convert()` for error handling and taskbar updating when failed.
        """

        self.update_progress(f"[bold yellow]Waiting for upload: {self.filename}[/]")

        async with self.skp_semaphore:
            if self.progress_bar:
                self.progress_bar.start_task(self.task_id)

            await self.convert_skp_to_blend()

        logger.info(f"Converted {self.filename} -> {self.blend_save_path.name}")
        self.update_progress(
            f"[bold blue]Waiting for Blender: {self.blend_save_path.name}[/]"
        )

        async with self.blender_semaphore:
            await self.convert_blend_to_glb()

        logger.info(f"Converted {self.blend_save_path.name} -> {self.filename} (done)")
        self.update_progress(
            f"[bold green]✓ Done: {self.filename} -> {self.glb_save_path.name}[/]",
            advance=1,
        )

    async def convert(self, suppress_errors=False) -> bool:
        """
        Convert the file in `self.filepath` .skp -> .blend -> .glb

        Error messages will appear in `self.progress_bar` if set.

        Return whether the conversion succeeded.
        If suppress_errors=True, return False instead of raising.
        """
        try:
            await self._convert()
            return True

        except Exception as e:
            if self.progress_bar:
                self.update_progress(
                    f"[red]✗ Failed: {self.filename} ({type(e).__name__}: {e})"
                )
                self.progress_bar.stop_task(self.task_id)

            logger.error(
                f"Conversion of '{self.filename}' failed: ({type(e).__name__}: {e}"
            )

            if not suppress_errors:
                raise RuntimeError("Conversion of model failed") from e

            return False


async def main():
    conversion_progress = Progress(
        TextColumn("[bold blue]{task.description}"),
        BarColumn(bar_width=80),
        TextColumn("({task.completed}/{task.total})"),
        TimeElapsedColumn(),
        expand=True,
    )

    with Live(conversion_progress):
        async with httpx.AsyncClient() as client:
            # pyrefly: ignore[not-async]
            instance = await ConvertSkp(
                "njc-l2-hall",
                client,
                config={
                    "skp_folder": ".skp",
                    "blend_folder": "/tmp/blender",
                    "glb_folder": ".glb",
                },
                progress_bar=conversion_progress,
            )

            await instance.convert()


if __name__ == "__main__":
    logging.basicConfig(
        format="%(message)s", level=logging.NOTSET, handlers=[RichHandler()]
    )
    logging.getLogger("httpcore").setLevel(logging.DEBUG)
    asyncio.run(main())
