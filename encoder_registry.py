#!/usr/bin/env python3

from encoder_pipeline import EncoderPipeline
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor


class EncoderPipelineRegistry:
    def __init__(self, config):
        self.config = config
        self.pipelines = {}
        self.executor = ThreadPoolExecutor(int(config["sketchup"]["maxworkers"]))

    def get_pipeline(self, level_path: Path):
        level_name = level_path.name

        if level_name not in self.pipelines:
            self.pipelines[level_name] = EncoderPipeline(
                self.config,
                name=level_name
            )

        return self.pipelines[level_name]

    def trigger(self, file_path: Path):
        # .skp/v1/level_a/model.skp
        level_path = file_path.parent

        pipe = self.get_pipeline(level_path)

        self.executor.submit(pipe.run, file_path)

    def shutdown(self, wait=True):
        self.executor.shutdown(wait=wait)