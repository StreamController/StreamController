"""
Author: Qalthos
Year: 2024

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

import subprocess
import json
from loguru import logger as log

import gi
gi.require_version("Xdp", "1.0")
from gi.repository import Xdp

import globals as gl

# Import typing
from typing import TYPE_CHECKING, Any
if TYPE_CHECKING:
    from src.backend.WindowGrabber.WindowGrabber import WindowGrabber

class Sway(Integration):
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
        return [self._parse_window(client) for client in self._get_windows()]

    def get_active_window(self) -> Window:
        window_list = self._get_windows()

        for client in window_list:
            if not client["focused"]:
                continue
            return self._parse_window(client)

    def _walk_tree(self, node, windows: list[dict[str, Any]]):
        if "window_properties" in node or "app_id" in node:
           # Try to only add actual windows
           windows.append(node)

        if "nodes" in node:
           for child in node.get("nodes"):
               self._walk_tree(child, windows)
           for child in node.get("floating_nodes"):
               self._walk_tree(child, windows)

    def _get_windows(self) -> list[dict[str, Any]]:
        windows = []
        try:
            # Run the swaymsg command and capture the output
            command = "swaymsg -t get_tree"
            output = subprocess.check_output(f"{self.command_prefix}{command}", shell=True, text=True, cwd="/").strip()
            # Parse the JSON output into a Python list
            clients = json.loads(output)

            for output in clients.get("nodes", []):
                for workspace in output.get("nodes", []):
                    self._walk_tree(workspace, windows)

        except subprocess.CalledProcessError as e:
            log.error(f"An error occurred while running swaymsg: {e}")
        except json.JSONDecodeError as e:
            log.error(f"Failed to parse JSON: {e}")

        return windows

    def _parse_window(self, client: dict[str, Any]) -> Window:
        if "window_properties" in client:
            # XWindow clients are slightly differently organized
            props = client["window_properties"]
            return Window(props["class"], props["title"])
        else:
            return Window(client.get("app_id", ""), client["name"])

class WatchForActiveWindowChange(threading.Thread):
    def __init__(self, sway: Sway):
        super().__init__(name="WatchForActiveWindowChange", daemon=True)
        self.sway = sway

        self.last_active_window = sway.get_active_window()

    @log.catch
    def run(self) -> None:
        while gl.threads_running:
            time.sleep(0.2)
            new_active_window = self.sway.get_active_window()
            if new_active_window is None:
                continue
            if new_active_window == self.last_active_window:
                continue

            self.last_active_window = new_active_window
            self.sway.window_grabber.on_active_window_changed(new_active_window)
