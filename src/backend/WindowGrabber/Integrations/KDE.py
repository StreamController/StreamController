"""
Author: flifloo
Year: 2025

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
any later version.

This programm comes with ABSOLUTELY NO WARRANTY!

You should have received a copy of the GNU General Public License
along with this program. If not, see <https://www.gnu.org/licenses/>.
"""

import threading
import time
from src.backend.WindowGrabber.Integration import Integration
from src.backend.WindowGrabber.Window import Window

from subprocess import Popen, CalledProcessError, PIPE
from loguru import logger as log

import gi
gi.require_version("Xdp", "1.0")
from gi.repository import Xdp

import globals as gl

# Import typing
from typing import TYPE_CHECKING, Optional
if TYPE_CHECKING:
    from src.backend.WindowGrabber.WindowGrabber import WindowGrabber


class KDE(Integration):
    def __init__(self, window_grabber: "WindowGrabber"):
        super().__init__(window_grabber=window_grabber)

        portal = Xdp.Portal.new()

        self.flatpak = portal.running_under_flatpak()
        self.is_kdotool_installed = self.get_is_kdotool_installed()

        if self.is_kdotool_installed:
            self.start_active_window_change_thread()

    @log.catch
    def _run_command(self, command: list[str]) -> Optional[Popen]:
        if self.flatpak:
            command.insert(0, "flatpak-spawn")
            command.insert(1, "--host")
        try:
            return Popen(command, stdout=PIPE, cwd="/")
        except Exception as e:
            log.error(f"An error occurred while running {command}: {e}")

    @log.catch
    def get_is_kdotool_installed(self) -> bool:
        try:
            out = self._run_command(["kdotool", "--version"]).communicate()[0].decode("utf-8")
            return out not in ("", None)
        except Exception as e:
            log.error(f"An error occurred while running kdotool: {e}")
            return False

    @log.catch
    def start_active_window_change_thread(self):
        self.active_window_change_thread = WatchForActiveWindowChange(self)
        self.active_window_change_thread.start()

    @log.catch
    def get_all_windows(self) -> list[Window]:
        windows: list[Window] = []

        try:
            root = self._run_command(["kdotool", "search"])
            if root is None:
                return []
            stdout, _ = root.communicate()

            window_ids = stdout.decode().strip().split("\n")
            if len(window_ids) < 2:
                return windows
        except CalledProcessError as e:
            log.error(f"An error occurred while running kdotool: {e}")
            return windows

        for window_id in window_ids:
            window = self.get_window(window_id)
            if window is not None:
                windows.append(window)

        return windows

    @log.catch
    def get_active_window(self) -> Window:
        try:
            kdotool = self._run_command(["kdotool", "getactivewindow"])
            if kdotool is None:
                return
            stdout, _ = kdotool.communicate()
            window_id = stdout.decode().strip()
            if len(window_id) == 0:
                return

            return self.get_window(window_id)

        except CalledProcessError as e:
            log.error(f"An error occurred while running kdotool: {e}")

    @log.catch
    def get_window(self, window_id: str) -> Optional[Window]:
        title = self.get_title(window_id)
        class_name = self.get_class(window_id)
        if title is None or class_name is None:
            return
        return Window(class_name, title)

    @log.catch
    def get_title(self, window_id: str) -> Optional[str]:
        try:
            kdotool = self._run_command(["kdotool", "getwindowname", window_id])
            if kdotool is None:
                return
            title = kdotool.communicate()[0].decode().strip()
            if title is None or len(title) < 2:
                return
            return title
        except CalledProcessError as e:
            log.error(f"An error occurred while running kdotool: {e}")

    @log.catch
    def get_class(self, window_id: str) -> Optional[str]:
        try:
            kdotool = self._run_command(["kdotool", "getwindowclassname", window_id])
            if kdotool is None:
                return
            window_class = kdotool.communicate()[0].decode().strip()
            if window_class is None or len(window_class) < 4:
                return
            return window_class
        except CalledProcessError as e:
            log.error(f"An error occurred while running kdotool: {e}")


class WatchForActiveWindowChange(threading.Thread):
    def __init__(self, kde: KDE):
        super().__init__(name="WatchForActiveWindowChange", daemon=True)
        self.kde = kde

        self.last_active_window = self.kde.get_active_window()

    @log.catch
    def run(self) -> None:
        while gl.threads_running:
            time.sleep(0.2)
            new_active_window = self.kde.get_active_window()
            if new_active_window is None:
                continue
            if new_active_window == self.last_active_window:
                continue

            self.last_active_window = new_active_window
            self.kde.window_grabber.on_active_window_changed(new_active_window)
