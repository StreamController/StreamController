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

import os
import re
import shutil
import threading
import time
from src.backend.WindowGrabber.Integration import Integration
from src.backend.WindowGrabber.Window import Window

from subprocess import Popen, CalledProcessError, PIPE
from loguru import logger as log

# Import globals first to get IS_MAC
import globals as gl

import gi

if not gl.IS_MAC:
    gi.require_version("Xdp", "1.0")
    from gi.repository import Xdp

# Import typing
from typing import TYPE_CHECKING, Optional
if TYPE_CHECKING:
    from src.backend.WindowGrabber.WindowGrabber import WindowGrabber


class KDE(Integration):
    KWIN_SCRIPT_NAME = "streamcontroller-window-watcher"

    def __init__(self, window_grabber: "WindowGrabber"):
        super().__init__(window_grabber=window_grabber)

        self.flatpak = False
        if not gl.IS_MAC:
            portal = Xdp.Portal.new()
            self.flatpak = portal.running_under_flatpak()

        self.is_kdotool_installed = self.get_is_kdotool_installed()

        # Preferred: a KWin script reports window changes through our DBus API
        # (NotifyForegroundWindow), so nothing has to be polled. kdotool polling
        # stays as the fallback, e.g. for KWin versions without the scripting API.
        if self.load_kwin_script():
            log.info("KDE: active window is reported by a KWin script, no polling")
        elif self.is_kdotool_installed:
            self.start_active_window_change_thread()

    @log.catch
    def load_kwin_script(self) -> bool:
        source = os.path.join(os.path.dirname(os.path.abspath(__file__)), "kde_window_watcher.js")
        # KWin runs on the host and has to read the file: the data dir is shared
        # with the host, the Flatpak's /app is not.
        script_dir = os.path.join(gl.DATA_PATH, "cache")
        os.makedirs(script_dir, exist_ok=True)
        script = os.path.join(script_dir, "kde_window_watcher.js")
        shutil.copyfile(source, script)

        # A copy from an earlier run would report twice
        self._kwin_call("/Scripting", "org.kde.kwin.Scripting.unloadScript", self.KWIN_SCRIPT_NAME)
        loaded = self._kwin_call("/Scripting", "org.kde.kwin.Scripting.loadScript", script, self.KWIN_SCRIPT_NAME)
        match = re.search(r"-?\d+", loaded or "")
        if match is None or int(match.group()) < 0:
            log.warning(f"KDE: could not load the KWin window watcher script: {loaded!r}")
            return False
        script_id = match.group()
        # Plasma 6 exposes loaded scripts as /Scripting/Script<id>, Plasma 5 as /<id>
        for path in (f"/Scripting/Script{script_id}", f"/{script_id}"):
            if self._kwin_call(path, "org.kde.kwin.Script.run") is not None:
                return True
        log.warning("KDE: loaded the KWin window watcher script but could not run it")
        return False

    def _kwin_call(self, path: str, method: str, *args: str) -> Optional[str]:
        """Call KWin over DBus (on the host when running as a Flatpak); None on failure."""
        process = self._run_command(["gdbus", "call", "--session", "--dest", "org.kde.KWin",
                                     "--object-path", path, "--method", method, *args])
        if process is None:
            return None
        stdout, _ = process.communicate()
        if process.returncode != 0:
            return None
        return stdout.decode().strip()

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
            root = self._run_command(["kdotool", "search", "."])
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
    def get_active_window_id(self) -> Optional[str]:
        try:
            kdotool = self._run_command(["kdotool", "getactivewindow"])
            if kdotool is None:
                return
            stdout, _ = kdotool.communicate()
            window_id = stdout.decode().strip()
            if len(window_id) == 0:
                return
            return window_id
        except CalledProcessError as e:
            log.error(f"An error occurred while running kdotool: {e}")

    @log.catch
    def get_active_window(self) -> Window:
        window_id = self.get_active_window_id()
        if window_id is None:
            return
        return self.get_window(window_id)

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
            if title is None:
                return
            if title == "":
                # When the desktop (plasmashell) has an empty title and
                # rejecting it means minimising every window is never seen as a
                # window change, so auto-change pages never fall back.
                time.sleep(0.1)
                kdotool = self._run_command(["kdotool", "getwindowname", window_id])
                if kdotool is None:
                    return
                title = kdotool.communicate()[0].decode().strip()
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

        self.last_window_id: Optional[str] = None
        self.last_active_window: Optional[Window] = None

        window_id = self.kde.get_active_window_id()
        if window_id is not None:
            self.last_window_id = window_id
            self.last_active_window = self.kde.get_window(window_id)

    @log.catch
    def run(self) -> None:
        while gl.threads_running:
            time.sleep(0.2)
            window_id = self.kde.get_active_window_id()
            if window_id is None:
                continue
            if window_id == self.last_window_id:
                continue

            self.last_window_id = window_id
            new_active_window = self.kde.get_window(window_id)
            if new_active_window is None:
                continue
            if new_active_window == self.last_active_window:
                continue

            self.last_active_window = new_active_window
            self.kde.window_grabber.on_active_window_changed(new_active_window)
