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

import globals as gl

# Import typing
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from src.backend.WindowGrabber.WindowGrabber import WindowGrabber

class X11(Integration):
    def __init__(self, window_grabber: "WindowGrabber"):
        super().__init__(window_grabber=window_grabber)

        portal = Xdp.Portal.new()
        self.command_prefix = None
        if portal.running_under_flatpak():
            self.command_prefix = "flatpak-spawn --host "

        self.start_active_window_change_thread()

    def _run_command(self, command: list[str]) -> subprocess.Popen:
        if self.command_prefix:
            command.insert(0, self.command_prefix)
        return subprocess.Popen(command, stdout=subprocess.PIPE, cwd="/")

    def start_active_window_change_thread(self):
        self.active_window_change_thread = WatchForActiveWindowChange(self)
        self.active_window_change_thread.start()

    def get_all_windows(self) -> list[Window]:
        windows: list[Window] = []

        try:
            root = self._run_command(["xprop", "-root", "_NET_CLIENT_LIST"])
            stdout, stderr = root.communicate()

            window_ids = stdout.decode().split("#")[1].strip().split(", ")
        except subprocess.CalledProcessError as e:
            log.error(f"An error occurred while running xprop: {e}")
            return windows

        for window_id in window_ids:
            title = self.get_title(window_id)
            class_name = self.get_class(window_id)

            if None in [title, class_name]:
                continue

            windows.append(Window(class_name, title))

        return windows

    def get_active_window(self) -> Window:
        try:
            root = self._run_command(["xprop", "-root", "_NET_ACTIVE_WINDOW"])
            stdout, stderr = root.communicate()
            window_id = stdout.strip().split()[-1]
        except subprocess.CalledProcessError as e:
            log.error(f"An error occurred while running xprop: {e}")
            return

        title = self.get_title(window_id)
        class_name = self.get_class(window_id)

        if None in [title, class_name]:
            return

        return Window(class_name, title)

    def get_title(self, window_id: str) -> str:
        if window_id == "0x0":
            return
        try:
            title_bytes = self._run_command(["xprop", "-id", window_id, "WM_NAME"]).communicate()[0]
            decoded = title_bytes.decode()
            split = decoded.split('"', 1)
            if len(split) < 2:
                return
            title = split[1].rstrip('"\n')
            return title
        except subprocess.CalledProcessError as e:
            log.error(f"An error occurred while running xprop: {e}")
            return

    def get_class(self, window_id: str) -> str:
        if window_id == "0x0":
            return
        try:
            class_bytes = self._run_command(["xprop", "-id", window_id, "WM_CLASS"]).communicate()[0]
            decoded = class_bytes.decode()
            split = decoded.split('"')
            if len(split) < 4:
                return
            window_class = split[3]
            return window_class
        except subprocess.CalledProcessError as e:
            log.error(f"An error occurred while running xprop: {e}")
        
class WatchForActiveWindowChange(threading.Thread):
    def __init__(self, x11: X11):
        super().__init__(name="WatchForActiveWindowChange", daemon=True)
        self.x11 = x11

        self.last_active_window = x11.get_active_window()

    @log.catch
    def run(self) -> None:
        while gl.threads_running:
            time.sleep(0.2)
            new_active_window = self.x11.get_active_window()
            if new_active_window is None:
                continue
            if new_active_window == self.last_active_window:
                continue

            self.last_active_window = new_active_window
            self.x11.window_grabber.on_active_window_changed(new_active_window)

