"""
Logging extensions.
"""
from __future__ import annotations

import logging
import logging.handlers
from collections.abc import Generator
from contextlib import contextmanager
from queue import Queue


@contextmanager
def capture_logs(log_queue: Queue[logging.LogRecord]) -> Generator[None]:
    handler = logging.handlers.QueueHandler(log_queue)
    root = logging.getLogger()

    try:
        root.addHandler(handler)
        yield

    finally:
        root.removeHandler(handler)
