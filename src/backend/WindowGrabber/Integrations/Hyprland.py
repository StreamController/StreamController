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

from re import sub
import threading
import time
from src.backend.WindowGrabber.Integration import Integration
from src.backend.WindowGrabber.Window import Window

import subprocess
import json
from loguru import logger as log

import gi
gi.require_version("Xdp", "1.0")
from gi.repository import Xdp

# Import typing
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from src.backend.WindowGrabber.WindowGrabber import WindowGrabber

class Hyprland(Integration):
    def __init__(self, window_grabber: "WindowGrabber"):
        super().__init__(window_grabber=window_grabber)

        portal = Xdp.Portal.new()
        self.command_prefix = ""
        if portal.running_under_flatpak():
            self.command_prefix = "flatpak-spawn --host "

        self.start_active_window_change_thread()
        
    def start_active_window_change_thread(self):
        self.active_window_change_thread = WatchForActiveWindowChange(self)
        self.active_window_change_thread.start()

    def get_all_windows(self) -> list[Window]:
        windows: list[Window] = []
        try:
            # Run the hyprctl command and capture the output
            output = subprocess.check_output(f"{self.command_prefix}hyprctl clients -j", shell=True, text=True).strip()
            # Parse the JSON output into a Python list
            clients = json.loads(output)

            for client in clients:
                if "class" in client and "title" in client:
                    windows.append(Window(client["class"], client["title"]))

        except subprocess.CalledProcessError as e:
            log.error(f"An error occurred while running hyprctl: {e}")
        except json.JSONDecodeError as e:
            log.error(f"Failed to parse JSON: {e}")

        return windows
    
    def get_active_window (self) -> Window:
        try:
            # Run the hyprctl command and capture the output
            output = subprocess.check_output(f"{self.command_prefix}hyprctl activewindow -j", shell=True, text=True).strip()
            # Parse the JSON output into a Python list
            client = json.loads(output)

            if "class" in client and "title" in client:
                return Window(client["class"], client["title"])
        except subprocess.CalledProcessError as e:
            log.error(f"An error occurred while running hyprctl: {e}")
        except json.JSONDecodeError as e:
            log.error(f"Failed to parse JSON: {e}")

        return None
    
class WatchForActiveWindowChange(threading.Thread):
    def __init__(self, hyprland: Hyprland):
        super().__init__(name="WatchForActiveWindowChange", daemon=True)
        self.hyprland = hyprland

        self.last_active_window = hyprland.get_active_window()

    def run(self) -> None:
        while True:
            time.sleep(0.2)
            new_active_window = self.hyprland.get_active_window()
            if new_active_window is None:
                continue
            if new_active_window == self.last_active_window:
                continue

            self.last_active_window = new_active_window
            self.hyprland.window_grabber.on_active_window_changed(new_active_window)

