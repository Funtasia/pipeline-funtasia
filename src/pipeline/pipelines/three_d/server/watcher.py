#!/usr/bin/env python3

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from pathlib import Path
import time

class SKPHandler(FileSystemEventHandler):
    def __init__(self, registry):
        self.registry = registry

    def on_modified(self, event):
        if event.is_directory:
            return

        path = Path(event.src_path)

        if path.suffix != ".skp":
            return
        self.registry.trigger(path)


def init_watcher(root_path, registry):
    event_handler = SKPHandler(registry)
    observer = Observer()

    observer.schedule(
        event_handler,
        str(root_path),
        recursive=True
    )

    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()

    observer.join()