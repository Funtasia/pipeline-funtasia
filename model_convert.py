from pathlib import Path
from urllib.parse import urlencode, urlunsplit, parse_qs, urlparse

import re
import time
import io
import zipfile
import asyncio
import httpx



async def make_request(client, url, method, *, timeout=120, content=None):
       
    try:
        if method == "GET":
            response = await client.get(
                url,
                timeout=timeout
            )
        elif method == "POST":
            response = await client.post(
                url,
                timeout=timeout,
                content=content
            )

        response.raise_for_status()
        return response

    except Exception as e:
        raise e  

    
class aobject(object):
    async def __new__(cls,*a,**kw):
        instance = super().__new__(cls)
        await instance.__init__(*a,**kw)
        return instance

    async def __init__(self):
        pass

class ConvertSkp(aobject):
    async def __init__(self,filepath: Path):
        self.filepath = filepath
        self.filename = filepath.name
        self.filesize = filepath.stat().st_size

        self.savefolder = Path("./.blend") / filepath.parent.relative_to(".skp") / filepath.name
        self.savefolder.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        self.blender_executable = Path(r"C:\Program Files\Blender Foundation\Blender 5.2\blender.exe")

        self.zip_path = self.savefolder.with_suffix(".zip")

        if self.zip_path.is_file():
            self.zip_path.unlink()

        self.blend_path = self.savefolder.with_suffix(".blend")

        if self.blend_path.is_file():
            self.blend_path.unlink()
        
        self.script_path = Path("./scripts/blender_script.py")
        
        self.semaphore = asyncio.Semaphore(1)


        self.file_params = {
            "name":filepath.name,
            "size":filepath.stat().st_size
        }


    async def get_env(self,client):
            
        response = await make_request(
            client,
            "https://3dencoder.com/SKP-to-blend",
            "GET",
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
    
        j = upload_params.get("j", [None])[0]
        s = upload_params.get("s", [None])[0]
        cuid = upload_params.get("cuid", [None])[0]
        

        return s,j,cuid
    
    async def get_token(self,client:httpx.AsyncClient,s,cuid):
    
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
    
        print(f"TokenUrl: {token_url}\n")

        response = await make_request(
            client,
            token_url,
            "GET",
            timeout=50
        )

        response = response.json()
        token = response.get("token")

        print(f"Token: {token}")
    
        return token

    async def get_fcode(self,client,token,s,j,cuid):
    
        upload_params = {
            "Method": "upload",
            "token": token,
            "client": "html5",
            "percen": 10,
            "s":s,
            "j":j,
            "cuid":cuid
        } | self.file_params
    
        upload_url = urlunsplit((
            "https",
            "e1.3dwhere.com",
            "/eupload.ashx",
            urlencode(upload_params),
            ""
        ))
    
        print("Upload:", upload_url, "\n")

        try:
            with self.filepath.open("rb") as f:
    
                upload_res = await client.post(
                    upload_url,
                    content=f.read(),
                    timeout=240
                )
    
            upload_res.raise_for_status()
    
            upload_data = upload_res.json()
            fcode = upload_data.get("message")
    
        except Exception as e:
            print("Failed to upload .skp ")
            print(repr(e))
            return None
        
    
        return fcode

    async def get_zipurl(self,client,fcode):
    
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
    
        print(f"Zipurl URL: {zipurl_url}")
    
        start = time.monotonic()
    
        while zipurl is None:
    
            try:
                zipurl_res = await client.get(
                    zipurl_url,
                    timeout=10
                )
    
                zipurl_res.raise_for_status()
    
                zipurl_data = zipurl_res.json()
    
                print(zipurl_data)
    
                zipurl = zipurl_data.get("zipfile")
    
                print(f"Zip URL: {zipurl}")
    
            except Exception as e:
                print("Request for zip url failed")
                print(e)
    
            if time.monotonic() - start > 120:
                break
    
            await asyncio.sleep(2)
    
        return zipurl
    
    async def save_zipfile(self,client,zipurl):
    
        try:
            zip_res = await client.get(
                zipurl,
                timeout=240
            )
    
            zip_res.raise_for_status()
    
        except Exception as e:
            print("Request for zip file failed")
            print(repr(e))
            return None
    
        print("Obtained Response for Zip File")
    

    

    
        self.zip_path.write_bytes(zip_res.content)
    
        with zipfile.ZipFile(
            io.BytesIO(zip_res.content)
        ) as z:
    
            file = z.namelist()[0]
    
            data = z.read(file)
    
            self.blend_path.write_bytes(data)

        return True
    

    @staticmethod
    async def first_success(tasks):
        pending = set(tasks)
    
        while pending:
            done, pending = await asyncio.wait(
                pending,
                return_when=asyncio.FIRST_COMPLETED
            )
    
            for task in done:
                try:
                    result = task.result()
                except Exception as e:
                    print(f"Attempt failed: {repr(e)}")
                    continue
    
                if result:
                    # We got our zip URL.
                    # Cancel every other conversion.
                    for other in pending:
                        other.cancel()
    
                    await asyncio.gather(
                        *pending,
                        return_exceptions=True
                    )
    
                    return result
    
        return None

    async def _convert(self, client):
        s, j, cuid = await self.get_env(client)

        token = await self.get_token(client, s, cuid)

        if token is None:
            return None

        fcode = await self.get_fcode(
            client,
            token,
            s,
            j,
            cuid
        )

        if fcode is None:
            return None

        zipurl = await self.get_zipurl(
            client,
            fcode
        )

        if zipurl is None:
            return None

        return zipurl
            
        
    async def run_blender(self):
        
        async with self.semaphore:

            command = [
                str(self.blender_executable),
                "--background",
                str(self.blend_path),
                "--python",
                str(self.script_path),
            ]

            print(f"Starting Blender: {self.blend_path}")

            process = await asyncio.create_subprocess_exec(
                *command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
            )

            stdout, _ = await process.communicate()

            output = stdout.decode(errors="replace")

            print(output)

            if process.returncode != 0:
                print(
                    f"Blender failed for {self.blend_path} "
                    f"(exit code {process.returncode})"
                )
                return False

            print(f"Blender completed: {self.blend_path}")
            return True
    
    async def convert(self):
        async with httpx.AsyncClient() as client:
            convert_tasks = [
                asyncio.create_task(
                    self._convert(client)
                )
                for _ in range(4)
            ]
    
            zipurl = await self.first_success(convert_tasks)
    
            if zipurl is None:
                return False
    
            print(f"Winning zip URL: {zipurl}")
    
            await self.save_zipfile(
                client,
                zipurl
            )

        await self.run_blender()

async def main():
    model = "b3"
    instance = await ConvertSkp(Path(f".skp/njc-{model}/njc-{model}.skp"))
    print(repr(instance.savefolder))
    await instance.convert()


if __name__ == "__main__":
    asyncio.run(main())