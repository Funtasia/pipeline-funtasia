#!/usr/bin/env python3

"""
server.py — run alongside dev.py to serve pipeline logs over HTTP.

Usage:
    uvicorn log_server:app --reload --port 8000

Then open logs.html in a browser.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pathlib import Path

from config import Config
from .encoder_registry import EncoderPipelineRegistry
from ._log import init_logging
from .watcher import init_watcher
import threading

init_logging()
config = Config.load()
registry = EncoderPipelineRegistry(config)

# Start watcher in background thread
root = Path(".skp") / Path(config["general"]["version"])
watcher_thread = threading.Thread(
    target=init_watcher,
    args=(root, registry),
    daemon=True
)
watcher_thread.start()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)


@app.get("/levels")
def get_levels():
    """Return all known pipeline names."""
    return {"levels": list(registry.pipelines.keys())}


@app.get("/logs/{level_name}")
def get_logs(level_name: str):
    """Drain and return buffered log records for a pipeline."""
    pipe = registry.pipelines.get(level_name)
    if pipe is None:
        return {"records": [], "error": "unknown level"}
    return {"records": pipe.buffer.flush_records()}


@app.get("/")
def serve_ui():
    return FileResponse("logs.html")