import inspect
from dataclasses import dataclass
from loguru import logger

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

            logger.log(f"{self.name}_{log_level.name}", message, function=function_name, line=line_number)

        setattr(self, log_level.method_name, log_method.__get__(self))

    def add_sink(self):
        def log_filter(record):
            if record["level"].name.startswith(f"{self.config.name}_"):
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
            format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {name} | {extra[function]}:{extra[line]} - {message}"
        )

    def _log(self, level, message, *args, **kwargs):
        logger.log(level, message, *args, **kwargs)