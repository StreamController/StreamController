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

from src.backend.WindowGrabber.Window import Window

# Import typing
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from src.backend.WindowGrabber.WindowGrabber import WindowGrabber

class Integration:
    def __init__(self, window_grabber: "WindowGrabber") -> None:
        self.window_grabber = window_grabber
    
    def get_all_windows(self) -> list[Window]:
        return []
    
    def get_active_window(self) -> Window:
        return None
    
    def close(self) -> None:
        return None