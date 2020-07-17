import logging
import sys
from pathlib import Path
from typing import Any

import loguru

LOGGER_FORMAT: str = r"<level> <v>{level:^10}</v> [{time:YYYY/MM/DD} {time:HH:mm:ss.SSS} <d>{module}:{name}</d>]</level> <u>{message}</>"
LOGGER_LEVEL: int = 10
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
