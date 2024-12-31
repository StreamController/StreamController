from abc import ABC
from multiprocessing.context import BaseContext
from loguru import logger
from typing import Optional, Union

class CustomLogger(ABC):
    TRACE: str = None
    DEBUG: str = None
    INFO: str = None
    SUCCESS: str = None
    WARNING: str = None
    ERROR: str = None
    CRITICAL: str = None
    FILTER: str = None

    def __init__(self, colors: dict[str, str] = None):
        level_config = {
            self.TRACE:    {"priority": 5,  "color": "<dim>"},
            self.DEBUG:    {"priority": 10, "color": "<blue>"},
            self.INFO:     {"priority": 20, "color": "<white>"},
            self.SUCCESS:  {"priority": 25, "color": "<green>"},
            self.WARNING:  {"priority": 30, "color": "<yellow>"},
            self.ERROR:    {"priority": 40, "color": "<red>"},
            self.CRITICAL: {"priority": 50, "color": "<bold><red>"},
        }
        colors = colors or {}

        for level, config in level_config.items():
            color = colors.get(level, config.get("color", None))
            priority = config.get("priority", None)
            if color and priority:
                logger.level(level, no=priority, color=color)

    def filter(self, record):
        return self.FILTER in record["level"].name

    def _log(self, level, message, *args, **kwargs):
        if level is None:
            message = "This level does not exist"
            logger.warning(message, *args, **kwargs)
        else:
            logger.log(level, message, *args, **kwargs)

    def trace(self, message, *args, **kwargs):
        self._log(self.TRACE, message, *args, **kwargs)

    def debug(self, message, *args, **kwargs):
        self._log(self.DEBUG, message, *args, **kwargs)

    def info(self, message, *args, **kwargs):
        self._log(self.INFO, message, *args, **kwargs)

    def success(self, message, *args, **kwargs):
        self._log(self.SUCCESS, message, *args, **kwargs)

    def warning(self, message, *args, **kwargs):
        self._log(self.WARNING, message, *args, **kwargs)

    def error(self, message, *args, **kwargs):
        self._log(self.ERROR, message, *args, **kwargs)

    def critical(self, message, *args, **kwargs):
        self._log(self.CRITICAL, message, *args, **kwargs)