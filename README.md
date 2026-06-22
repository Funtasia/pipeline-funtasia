# Encoder Pipeline

## How it works

The script obtains a set of config info: `cuid`,`s` and `j` via making a request to https://3dencoder.com/SKP-to-blend. Subsequently, it stores these config information in a `Vars` class. The pipeline then makes request to the host server and fetches the zip file contianing the converted file.

The zip file is then unzipped and stored. The main pipeline will then call on a script to post process the blender file, which exports the final model accordingly.

# Quickstart
## Prerequisites
* Python >= 3.13 (older Python MIGHT be supported, but no guarantees)
* Git
* Blender
* Sketchup (For Linux: installed as WINE app)

## For all platforms:
1. Head to the releases and download the latest `setup.pyz`.
2. Run `setup.pyz` using Python. (UNIX users can also run it directly!)

## For Linux:
<!--PATs only used while this repo is private, RMB TO CHANGE WHEN PUBLIC-->
This method directly downloads `setup.pyz` from the latest release and runs it.

1. Get a Personal Access Token (PAT) for the Funtasia organisation. [Handy StackOverflow answer with images.](https://stackoverflow.com/a/78397297) PLEASE NOTE DOWN THE TOKEN SOMEWHERE OR YOU WILL LOSE IT!
2. Set the environment variable $GHTOKEN. (e.g. `GHTOKEN=<PAT TOKEN>`)
3. Run the following code to get the latest `setup.pyz` script (if `jq` is installed)
```bash
curl -s -H "Authorization: token $GHTOKEN" "https://api.github.com/repos/Funtasia/pipeline-funtasia/releases/latest" \
  | jq -r '.assets[] | select(.name=="setup.pyz") | .url' \
  | xargs -I{} curl -L -H "Authorization: token $GHTOKEN" -H "Accept: application/octet-stream" -o setup.pyz {} \
&& chmod +x ./setup.pyz \
&& ./setup.pyz
```
Or if `jq` is not installed:
```bash
curl -s -H "Authorization: token $GHTOKEN" "https://api.github.com/repos/Funtasia/pipeline-funtasia/releases/latest" \
  | grep -oP 'https://api\.github\.com/repos/[^/]+/[^/]+/releases/assets/\d+' \
  | xargs -I{} curl -L -H "Authorization: token $GHTOKEN" -H "Accept: application/octet-stream" -o setup.pyz {} \
&& chmod +x ./setup.pyz \
&& ./setup.pyz
```

# I'm ngl i honestly dk what to put here, whoever you are, you got this trust.