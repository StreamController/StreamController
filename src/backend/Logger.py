import inspect
import os
import sys
from dataclasses import dataclass
from pathlib import Path

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
    base_log_level: str = "DEBUG"
    rotation: str | None = None
    retention: str | None = None
    compression: str | None = None
    backtrace: bool = False
    diagnose: bool = False
    catch: bool = False
    enqueue: bool = False

class Logger:
    def __init__(self, config: LoggerConfig, levels: list[Loglevel]):
        self.config = config
        self.name = config.name
        self.levels: dict[str, Loglevel] = {}

        self._register_log_levels(levels)
        self._add_file_sink()
        self._add_console_sink()

    def _register_log_levels(self, levels: list[Loglevel]):
        for level in levels:
            full_name = f"{self.name}_{level.name}"
            logger.level(full_name, no=level.priority, color=level.color)
            self.levels[level.name] = level
            self._bind_method(level)

    def _bind_method(self, level: Loglevel):
        def log_method(message: str, *args, **kwargs):
            # Fallback to empty if frame lookup fails
            file_name = function_name = line_number = "?"
            try:
                frame = inspect.currentframe()
                caller = frame.f_back

                file_path = Path(caller.f_code.co_filename)
                rel_path = os.path.relpath(str(file_path), gl.top_level_dir)
                file_name = rel_path.replace(os.sep, ".").removesuffix(".py")

                function_name = caller.f_code.co_name
                line_number = caller.f_lineno
            except Exception as e:
                print(f"Logger context error: {e}")
            finally:
                del frame  # Avoid reference cycles

            # Build context manually
            static_extra = {
                "file_name": file_name,
                "function": function_name,
                "line": line_number
            }

            # Dynamic binds from kwargs
            dynamic_extra = {k: kwargs.pop(k) for k in list(kwargs) if k not in ("exc_info", "stack_info")}

            full_extra = {**static_extra, **dynamic_extra}

            # Compose full log level name
            full_level_name = f"{self.name}_{level.name}"

            # Send log with merged extra context
            logger.log(full_level_name, message, *args, line=line_number, function=function_name, file_name=file_name,  extra=full_extra, **kwargs)

        setattr(self, level.method_name, log_method)

    def _add_file_sink(self):
        def file_filter(record):
            return record["level"].name.startswith(f"{self.name}_")

        logger.add(
            sink=self.config.log_file_path,
            level=self.config.base_log_level,
            rotation=self.config.rotation,
            retention=self.config.retention,
            compression=self.config.compression,
            backtrace=self.config.backtrace,
            diagnose=self.config.diagnose,
            catch=self.config.catch,
            enqueue=self.config.enqueue,
            filter=file_filter,
            format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <12} | {extra[file_name]} | {extra[function]}:{extra[line]} - {message} : {extra[extra]}"
        )

    def _add_console_sink(self):
        def console_filter(record):
            return record["level"].name.startswith(f"{self.name}_")

        logger.add(
            sink=sys.stdout,
            level=self.config.base_log_level,
            colorize=True,
            filter=console_filter,
            format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <12}</level> | <cyan>{extra[file_name]}</cyan>:<blue>{extra[function]}</blue>:<magenta>{extra[line]}</magenta> - <level>{message}</level>  <italic><white>{extra[extra]}</white></italic>"
        )

    def log(self, level_name: str, message: str, *args, **kwargs):
        """Generic logging if you want to pass a level string directly"""
        full_level_name = f"{self.name}_{level_name}"
        logger.log(full_level_name, message, *args, **kwargs)