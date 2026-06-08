from pathlib import Path
from util import load_config
from registry import PipelineRegistry
from watcher import start_watching
from logger import setup_logging

config = load_config()

registry = PipelineRegistry(config)

root = Path(".skp") / Path(config["general"]["version"])

setup_logging()
start_watching(root, registry)