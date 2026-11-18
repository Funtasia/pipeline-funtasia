# Installation

Due to the nature of some dependencies being compiled and therefore having a different binary per OS per python version per cpu architecture, it is not possible to bundle the entire project into a .pyz executable. Thus, the best way to manage these different machines is using pip, which will automatically pick the correct version to install. To prevent pip from installing `nipple` system-wide (you probably don't want/need this), we can either use a virtual environment (`python -m venv`), or use a tool that automatically creates a virtual environment for us, such as pipx. (pipx is also recommended as an alternative to pip for [externally managed environments](https://packaging.python.org/en/latest/specifications/externally-managed-environments/#guide-users-towards-virtual-environments)).

Furthermore, while most packages are installed via PyPI, I am too lazy to upload and maintain it there. <!--Also nobody going to read this except me, so why tf would i even bother???--><!--Also it's on test.pypi.org instead lmao haha--> Luckily, [pip supports installing from a VCS](https://pip.pypa.io/en/stable/topics/vcs-support/).

Therefore, install nipple by:
```sh
pipx install git+https://github.com/Funtasia/pipeline-funtasia
```
or the long way:
```sh
# on UNIX / git bash
cd path/to/project/directory
python -m venv .venv
. .venv/bin/activate # or . .venv/Scripts/activate on windows git bash
pip install git+https://github.com/Funtasia/pipeline-funtasia
```

Now you can access nipple!
```
nipple
```
## deprecated installation methods

#### individual scripts in setup/
Was hard to maintain, and especially more difficult when windows has script execution off by default, making it harder to activate virtual environment. Furthermore it is hard to ensure that the user is in the correct directory before running the script, assuming the user is unfamiliar with the terminal.

Therefore, scripts were abandoned?

#### .pyz in github actions release
This was viable when the dependencies all had pure python, which changed in typer>=0.29 with pydantic as required dependency. There are also plans for including fastapi, which will most certainly solidify pydantic as a dependency. Thus, .pyz with deps abandoned.
