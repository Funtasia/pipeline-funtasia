# Encoder Pipeline

## How it works

The script obtains a set of config info: `cuid`,`s` and `j` via making a request to https://3dencoder.com/SKP-to-blend. Subsequently, it stores these config information in a `Vars` class. The pipeline then makes request to the host server and fetches the zip file contianing the converted file.

The zip file is then unzipped and stored. The main pipeline will then call on a script to post process the blender file, which exports the final model accordingly.

# I'm ngl i honestly dk what to put here, whoever you are, you got this trust.