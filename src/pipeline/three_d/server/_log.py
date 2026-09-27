#!/usr/bin/env python3

import logging

SUCCESS = 25
logging.addLevelName(SUCCESS, "SUCCESS")


class BufferHandler(logging.Handler):
    """Captures log records into an in-memory list for a single pipeline."""

    def __init__(self):
        super().__init__()
        self.records: list[dict] = []

    def emit(self, record: logging.LogRecord):
        self.records.append({
            "level":   record.levelname,
            "func":    record.funcName,
            "message": self.format(record),
            "time":    record.created,
        })

    def flush_records(self) -> list[dict]:
        """Return and clear all buffered records."""
        records, self.records = self.records, []
        return records



class EncoderPipelineLogger(logging.LoggerAdapter):
    """
    Logger adapter for EncoderPipeline with consistent formatting and helper methods.
    Output goes to stdout.
    """
    _LOG_FORMAT = "[PIPELINE:%(pipeline)s] %(levelname)-8s %(message)s"

    def __init__(self, pipeline: str, name: str = "encoder_pipeline") -> None:
        logger = logging.getLogger(name)
        logger.setLevel(logging.DEBUG)

        if not logger.handlers:
            handler = logging.StreamHandler()  # stdout
            handler.setFormatter(logging.Formatter(self._LOG_FORMAT))
            logger.addHandler(handler)

        super().__init__(logger, extra={"pipeline": pipeline})

    # Convenience wrappers ------------------------------------------------

    def info(self, msg: str, *args, **kwargs) -> None:
        self.logger.info(msg, *args, stacklevel=2, **kwargs)

    def error(self, msg: str, *args, **kwargs) -> None:
        self.logger.error(msg, *args, stacklevel=2, **kwargs)

    def success(self, msg: str) -> None:
        self.logger.log(SUCCESS, msg, stacklevel=2)


def initEncoderLogger(name: str) -> tuple[EncoderPipelineLogger, BufferHandler]:
    """
    Create an isolated logger + buffer for a single pipeline.
    Returns both so the registry can hold onto the buffer for the UI later.
    """
    logger = logging.getLogger(f"pipeline.{name}")
    logger.setLevel(logging.DEBUG)
    logger.propagate = False  # don't bubble up to root logger

    # stdout handler — same format as before
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(
        logging.Formatter("[%(levelname)-7s] [%(funcName)-15s] %(message)s")
    )
    logger.addHandler(stream_handler)

    # in-memory buffer for the UI
    buffer = BufferHandler()
    logger.addHandler(buffer)

    adapter = EncoderPipelineLogger(logger, {"pipeline": name})
    return adapter, buffer


def init_logging():
    logging.basicConfig(
        format="[%(levelname)-7s] [%(funcName)-15s] %(message)s",
        level=logging.INFO
    )