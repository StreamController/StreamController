"""
Author: Core447
Year: 2024

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
any later version.

This programm comes with ABSOLUTELY NO WARRANTY!

You should have received a copy of the GNU General Public License
along with this program. If not, see <https://www.gnu.org/licenses/>.
"""

from typing import Any
from loguru import logger as log

class DummyPage:
    """
    A dummy that accepts any method calls and does nothing
    """
    def __init__(self) -> None:
        pass

    def __setattr__(self, name: str, value: Any) -> None:
        log.trace(f"Dummy page: {name} = {value}")
        

    def __getattr__(self, name: str) -> Any:
        log.trace(f"Dummy page: {name}")
        # Return a lambda that does nothing
        return lambda *args, **kwargs: None