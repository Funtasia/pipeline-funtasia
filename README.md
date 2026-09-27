# Nipple (fuNtasIa PiPeLinE)

## How it works

The script obtains a set of config info: `cuid`,`s` and `j` via making a request to https://3dencoder.com/SKP-to-blend. Subsequently, it stores these config information in a `Vars` class. The pipeline then makes request to the host server and fetches the zip file contianing the converted file.

The zip file is then unzipped and stored. The main pipeline will then call on a script to post process the blender file, which exports the final model accordingly.

# Quickstart

## Prerequisites
* Python >= 3.13 (older Python MIGHT be supported, but no guarantees)
* Git
* Blender
* Sketchup (For Linux: installed as WINE app)

## For *NIX:
```
curl -fsSL https://github.com/Funtasia/pipeline-funtasia/raw/refs/heads/main/setup/setup.sh | sh
```

## For Windows:
```
irm https://github.com/Funtasia/pipeline-funtasia/raw/refs/heads/main/setup/setup.ps1 | iex
```

## Manual Install:
1. Create a Python virtual environment (`python -m venv .venv`)
2. Activate the virtual environment
3. `pip install git+https://github.com/Funtasia/pipeline-funtasia`
4. `nipple setup`

# Installation of Relevant Resources

**Blender**

Blender can be downloaded via Steam, from the [official blender website](https://www.blender.org/download/), or from a package manager of your choice. Ensure that it is available in $PATH.

# I'm ngl i honestly dk what to put here, whoever you are, you got this trust.