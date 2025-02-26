import inspect
import os
from dataclasses import dataclass
from loguru import logger
import globals as gl

@dataclass
class Loglevel:
    name: str
    method_name: str
    priority: int
    color: str

@dataclass
class LoggerConfig:
    name: str

    log_file_path: str
    base_log_level: str
    rotation: str
    retention: str
    compression: str

class Logger:
    def __init__(self, config: LoggerConfig, log_level: list[Loglevel]):
        self.name = config.name

        self.config = config
        self.log_level: dict[str, Loglevel] = {}

        for level in log_level:
            self.add_log_level(level)
            self.log_level[level.name] = level
        self.add_sink()

    def add_log_level(self, log_level: Loglevel):
        logger.level(
            name=f"{self.name}_{log_level.name}",
            no=log_level.priority,
            color=f"{log_level.color}")

        def log_method(self, message, *args, **kwargs):
            caller = inspect.stack()[1]
            function_name = caller.function
            line_number = caller.lineno

            file_path = caller.filename
            base_path = gl.DATA_PATH

            relative_path = os.path.relpath(file_path, base_path)  # Get relative path
            relative_path = os.path.splitext(relative_path)[0]  # Remove .py extension
            relative_path = relative_path.replace(os.sep, ".")  # Convert to dot notation

            logger.log(f"{self.name}_{log_level.name}", message, file_name=relative_path, function=function_name, line=line_number)

        setattr(self, log_level.method_name, log_method.__get__(self))

    def add_sink(self):
        def log_filter(record):
            if record["level"].name.startswith(f"{self.config.name}_"):
                print(record)
                return True
            return False

        logger.add(
            sink=self.config.log_file_path,
            level=self.config.base_log_level,
            rotation=self.config.rotation,
            retention=self.config.retention,
            compression=self.config.compression,
            enqueue=True,
            filter=log_filter,
            format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level} | {extra[file_name]} | {extra[function]}:{extra[line]} - {message}"
        )

    def _log(self, level, message, *args, **kwargs):
        logger.log(level, message, *args, **kwargs)