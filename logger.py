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


class EndcoderPipelineLogger(logging.LoggerAdapter):
    def process(self, msg, kwargs):
        return f"[pipeline:{self.extra['pipeline']}] {msg}", kwargs


def make_pipeline_logger(name: str) -> tuple[EndcoderPipelineLogger, BufferHandler]:
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

    adapter = EndcoderPipelineLogger(logger, {"pipeline": name})
    return adapter, buffer


def setup_logging():
    logging.basicConfig(
        format="[%(levelname)-7s] [%(funcName)-15s] %(message)s",
        level=logging.INFO
    )