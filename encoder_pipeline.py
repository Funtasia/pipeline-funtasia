#!/usr/bin/env python

import sys
import re
import subprocess
import random
import urllib.parse
import requests
from pathlib import Path
import time
import zipfile
import io
from logger import make_pipeline_logger, SUCCESS, setup_logging
import logging
from util import load_config, extract_url, CONFIG_PATH


class Vars:
    def __init__(self, cuid, s, j):
        self.cuid = cuid
        self.s = s
        self.j = j
        self.uses_left = 3

    def use(self):
        self.uses_left -= 1


class EncoderPipeline:
    def __init__(self, config, name):
        self.config_path = CONFIG_PATH
        self.config = config

        self.logger, self.buffer = make_pipeline_logger(name)

        self.version = config["general"]["version"]

        self.backup_dir = Path(config["repos"]["MAINDIR"]) / config["repos"]["files"] / "converted"
        self.working_dir = Path(config["repos"]["MAINDIR"]) / config["repos"]["files"] / ".blend" 

        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self.working_dir.mkdir(parents=True, exist_ok=True)

        self.vars = None

    def log(self, msg):
        self.logger.info(msg, stacklevel=2)

    def error(self, msg):
        self.logger.error(msg, stacklevel=2)

    def success(self, msg):
        self.logger.log(SUCCESS, msg, stacklevel=2)

    def gen_vars(self):
        html = requests.get("https://3dencoder.com/SKP-to-blend", timeout=10).text

        upload_url = extract_url(r'uploadURL\s*:\s*"([^"]+)"', html)

        upload_params = urllib.parse.parse_qs(urllib.parse.urlparse(upload_url).query)

        j    = upload_params.get("j", [None])[0]
        cuid = upload_params.get("cuid", [None])[0]
        s    = upload_params.get("s", [None])[0]

        for i in [cuid, s, j]:
            if i is None:
                self.error(f"{i} not found")
        if None in (cuid, s, j):
            self.error("failed to initilise vars")
            return None

        self.success("initialising vars")
        self.log(f"cuid: {cuid}")
        self.log(f"s: {s}")
        self.log(f"j: {j}")
        return Vars(cuid, s, j)

    def get_vars(self):
        if self.vars and self.vars.uses_left > 0:
            return self.vars

        self.log("refreshing vars")
        self.vars = self.gen_vars()
        return self.vars

    def upload(self, filepath):
        path = Path(filepath)

        if not path.exists():
            self.error(f"file not found: {filepath}")
            return

        filename = path.name
        enc_filename = urllib.parse.quote(filename)

        file_size = path.stat().st_size

        mtime = path.stat().st_mtime
        raw_modified = time.strftime(
            "%a %b %d %Y %H:%M:%S GMT%z",
            time.localtime(mtime)
        )
        enc_modified = urllib.parse.quote(raw_modified)

        rnd = random.randint(10000, 99999)

        if (vars := self.get_vars()) is None:
            self.error("failed to obtain vars instance")
            return None

        cuid = vars.cuid
        s = vars.s
        j = vars.j

        self.log(f"file Name : {filename}")
        self.log(f"size      : {file_size} bytes")
        self.log(f"modified  : {raw_modified}")

        self.log("requesting upload token")
        token_url = (
            f"https://e1.3dwhere.com/eupload.ashx?"
            f"Method=tk&cuid={cuid}&s={s}"
            f"&name={enc_filename}&type=&size={file_size}"
            f"&modified={enc_modified}&{rnd}"
        )

        try:
            token_res = requests.get(token_url).json()
            token = token_res.get("token")

            if not token:
                self.error(f"token res: {token_res}")
                return

            self.success(f"token res: {token}")

        except Exception as e:
            self.error(e)
            return

        self.log("uploading .skp file")
        upload_url = (
            f"https://e1.3dwhere.com/eupload.ashx?"
            f"Method=upload&j={j}&cuid={cuid}&s={s}"
            f"&percen=10&token={token}&client=html5"
            f"&name={enc_filename}&size={file_size}"
        )

        headers = {
            "Content-Range": f"bytes 0-{file_size}/{file_size}"
        }

        try:
            with path.open("rb") as f:
                upload_res = requests.post(upload_url, headers=headers, data=f).json()

            self.success("uploaded sketchup file")
            vars.use()
            fcode = upload_res.get("message")
        except Exception as e:
            self.error(e)
        return fcode

    def fetch_zip_lnk(self, fcode):
        if fcode is None:
            self.error("fcode not found")
            return

        self.log("fetching zip link")

        info_url = (
            f"https://e1.3dwhere.com/json.aspx?"
            f"action=getinfo&fcode={fcode}"
        )

        try:
            info_res = {}
            start = time.time()
            while True:
                info_res = requests.get(info_url).json()

                zipfile_lnk = info_res.get("zipfile")
                if zipfile_lnk:
                    self.success(f"zipfile link: {zipfile_lnk}")
                    break

                time.sleep(2)
                if time.time() - start > 120:
                    self.error("timeout waiting for zipfile link")

            return zipfile_lnk

        except Exception as e:
            self.error(e)

    def extract(self, zip_url):
        backup_dir = self.backup_dir
        working_dir = self.working_dir
        version = self.version

        r = requests.get(zip_url)
        r.raise_for_status()
        self.success("fetched zip file")

        with zipfile.ZipFile(io.BytesIO(r.content)) as z:
            file = z.namelist()[0]
            self.log(f"unzipping: {file}")
            name = Path(file).stem

            target_subdir = Path(version) / name

            full_original = backup_dir / target_subdir / file
            full_working = working_dir / target_subdir / file

            self.log(f"target subdir: {target_subdir}")

            data = z.read(file)

            full_original.parent.mkdir(parents=True, exist_ok=True)
            full_working.parent.mkdir(parents=True, exist_ok=True)

            full_original.write_bytes(data)
            full_working.write_bytes(data)
            self.success("extrated zipfile")

    def _blend_path(self, stem: str) -> Path:
        """
        Resolve the .blend file location produced by 3dencoder.

        Layout: config["repos"]["files"] / .blend / config["general"]["version"] / <stem>.blend
        """
        parent  = Path(self.config["repos"]["MAINDIR"])
        rel_dir = Path(self.config["repos"]["files"]) / ".blend" / self.version
        return parent / rel_dir / f"{stem}.blend"

    # Re pattern that matches every line emitted by BlenderLogger:
    #   [BLENDER] LEVEL    message text
    _BLENDER_LINE = re.compile(
        r"^\[BLENDER\]\s+(?P<level>\w+)\s+(?P<message>.+)$"
    )

    # Map BlenderLogger levelnames → logger methods on self
    _LEVEL_DISPATCH: dict[str, str] = {
        "DEBUG":   "log",
        "INFO":    "log",
        "SUCCESS": "success",
        "WARNING": "error",
        "ERROR":   "error",
        "CRITICAL":"error",
    }

    def _relay_blender_line(self, raw: str) -> None:
        """
        Parse one line from Blender's stdout and re-emit via the encoder logger.

        Structured lines ([BLENDER] LEVEL msg) are dispatched to the matching
        level.  Unstructured lines (Blender's own boot noise) are emitted at
        DEBUG / log level so they're visible but don't pollute the output.
        """
        line = raw.rstrip()
        if not line:
            return

        m = self._BLENDER_LINE.match(line)
        if m:
            level   = m.group("level").upper()
            message = m.group("message")
            method  = self._LEVEL_DISPATCH.get(level, "log")
            getattr(self, method)(f"[blender] {message}")
        else:
            # Blender boot / bpy noise — forward at info level with a prefix
            self.log(f"[blender:raw] {line}")

    def _run_blender(self, blend_path: Path, config_path: Path) -> bool:
        """
        Invoke Blender headlessly on *blend_path*, running blender_pipeline.py.

        Streams stdout line-by-line into the encoder logger via _relay_blender_line().
        Returns True on success (exit code 0), False otherwise.
        """
        cmd = [
            "blender",
            "-b", str(blend_path),
            "-P", "blender_pipeline.py",
            "--",
            "--config", str(config_path),
        ]

        self.log(f"spawning blender: {blend_path.name}")
        self.log(f"command: {' '.join(cmd)}")

        try:
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,   # merge stderr → stdout so one stream
                text=True,
                bufsize=1,                  # line-buffered
            )

            for line in proc.stdout:
                self._relay_blender_line(line)

            proc.wait()

            if proc.returncode == 0:
                self.success(f"blender exited cleanly (code 0)")
                return True
            else:
                self.error(f"blender exited with code {proc.returncode}")
                return False

        except FileNotFoundError:
            self.error("blender executable not found — is it on PATH?")
            return False
        except Exception as e:
            self.error(f"blender subprocess error: {e}")
            return False

    def run(self, filepath):
        fcode = self.upload(filepath)
        if not fcode:
            return

        zip_url = self.fetch_zip_lnk(fcode)
        if not zip_url:
            return

        self.extract(zip_url)

        # Derive the .blend path from the original .skp stem
        stem       = Path(filepath).stem
        blend_path = self._blend_path(stem)

        if not blend_path.exists():
            self.error(f".blend file not found after extraction: {blend_path}")
            return

        ok = self._run_blender(blend_path, Path(self.config_path))
        if not ok:
            self.error(f"blender pipeline failed for '{stem}' — aborting")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python upload.py \"/path/to/file.skp\" ")
        sys.exit(1)
    setup_logging()

    CONFIG = load_config()
    fp          = sys.argv[1]
    pipe = EncoderPipeline(CONFIG, "test")
    pipe.run(fp)