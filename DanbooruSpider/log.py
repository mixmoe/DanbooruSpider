import logging
import sys
from pathlib import Path
from typing import Any

import loguru

from .config import Config

LogConfig = Config["general"]["log"]

LOGGER_FORMAT: str = LogConfig["format"].as_str()
LOGGER_LEVEL: str = LogConfig["level"].as_str().upper()
LOGGER_FILE_DIR: Path = Path(".") / "data" / "logs"

LOGGER_FILE_DIR.mkdir(exist_ok=True)


class _LoguruHandler(logging.Handler):
    def emit(self, record: Any) -> None:
        message = record.getMessage()
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        frame: Any = logging.currentframe()
        depth = 2
        while frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        loguru.logger.opt(depth=depth, exception=record.exc_info).log(level, message)


def loggerFactory() -> loguru.Logger:
    logger = loguru.logger
    logger.remove()
    logger.add(sys.stdout, enqueue=True, level=LOGGER_LEVEL, format=LOGGER_FORMAT)
    logger.add(
        str(LOGGER_FILE_DIR / "{time}.log"),
        enqueue=True,
        level=LOGGER_LEVEL,
        format=LOGGER_FORMAT,
        encoding="utf-8",
    )
    return logger.opt(colors=True)


logger = loggerFactory()
LoguruHandler = _LoguruHandler()
