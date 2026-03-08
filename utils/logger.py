import logging
import os
from logging.handlers import (
    QueueHandler,
    QueueListener,
    TimedRotatingFileHandler
)
import queue
import atexit
import json_log_formatter
import time

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG_DIR = os.path.join(BASE_DIR, ".RAGU", "logs")
os.makedirs(LOG_DIR, exist_ok=True)

log_queue = queue.Queue()
json_formatter = json_log_formatter.JSONFormatter()

listener = None


def _start_listener():
    global listener

    log_file = os.path.join(LOG_DIR, "app.log")

    fh = TimedRotatingFileHandler(
        log_file,
        when="midnight",
        interval=1,
        backupCount=30,
        encoding="utf-8",
        delay=True
    )
    fh.setFormatter(json_formatter)

    listener = QueueListener(
        log_queue,
        fh,
        respect_handler_level=True
    )
    listener.start()


_start_listener()


def _shutdown_listener():
    separator = '*' * 150
    if listener and listener.handlers:
        for handler in listener.handlers:
            if isinstance(handler, logging.FileHandler) or isinstance(handler, TimedRotatingFileHandler):
                if getattr(handler, 'stream', None):
                    try:
                        record = logging.LogRecord(
                            name="shutdown",
                            level=logging.INFO,
                            pathname=__file__,
                            lineno=0,
                            msg=separator,
                            args=(),
                            exc_info=None
                        )
                        record.created = time.time()
                        handler.emit(record)
                    except Exception:
                        pass

    if listener:
        listener.stop()


atexit.register(_shutdown_listener)


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    if logger.handlers:
        return logger

    queue_handler = QueueHandler(log_queue)
    logger.addHandler(queue_handler)

    logger.propagate = False

    return logger
