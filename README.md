# Nipple (fuNtasIa PiPeLinE)

## How it works

The script spoofs a `cuid` and obtains token and upload urls `tkurl` and `upurl` via making a request to https://api.3dwhere.com/account/url/convupload. Subsequently, it uses these config information to make necessary requests to upload the file to the server and download the converted zip file.

The zip file is then unzipped and stored. The main pipeline will then call on a script to post process the blender file, which exports the final model accordingly.

# Quickstart

## Prerequisites
* Python >= 3.13 (older Python MIGHT be supported, but no guarantees)
* Git
* Blender
* Sketchup: For development of models

## For *NIX:
```
curl -fsSL https://github.com/Funtasia/pipeline-funtasia/raw/refs/heads/main/setup/setup.sh | sh
```

## For Windows:
```
irm https://github.com/Funtasia/pipeline-funtasia/raw/refs/heads/main/setup/setup.ps1 | iex
```

## Manual Install:
1. Create a Python virtual environment (`python -m venv .venv`) in the Funtasia root folder
2. Activate the virtual environment (`.\venv\Scripts\activate` or `. .venv/bin/activate`)
3. `pip install git+https://github.com/Funtasia/pipeline-funtasia`
4. `nipple setup`

# Installation of Relevant Resources

**Blender**

Blender can be downloaded from the [official blender website](https://www.blender.org/download/), from [Steam](https://store.steampowered.com/app/365670/Blender/), or from a package manager of your choice. Ensure that it is available in $PATH (typing `blender`/`blender.exe` in a terminal should open it).

**Git**

If you still don't have it, you can install git from the [official website](https://git-scm.com/install/). 
<!--What maniac doesn't have git but wants to do software development??-->

**Sketchup**

Sketchup Make 2017 should be free to download on Internet Archive, but more recent versions might be found elsewhere. Regardless, it is only required if you are remaking skp files to convert.



<!--I'm ngl i honestly dk what to put here, whoever you are, you got this trust.-->