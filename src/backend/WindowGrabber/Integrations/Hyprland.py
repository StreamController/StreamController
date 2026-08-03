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

import os
import socket
import threading
from src.backend.WindowGrabber.Integration import Integration
from src.backend.WindowGrabber.Window import Window

import subprocess
import json
from loguru import logger as log

# Import globals first to get IS_MAC
import globals as gl

import gi

if not gl.IS_MAC:
    gi.require_version("Xdp", "1.0")
    from gi.repository import Xdp

# Import typing
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from src.backend.WindowGrabber.WindowGrabber import WindowGrabber

class Hyprland(Integration):
    def __init__(self, window_grabber: "WindowGrabber"):
        super().__init__(window_grabber=window_grabber)

        self.command_prefix = ""
        if not gl.IS_MAC:
            portal = Xdp.Portal.new()
            if portal.running_under_flatpak():
                self.command_prefix = "flatpak-spawn --host "

        self._socket_path = self._find_socket2_path()
        self.start_active_window_change_thread()

    def _find_socket2_path(self) -> str | None:
        """Find the Hyprland IPC event socket (socket2).

        Returns the path to the socket, or None if not found.
        """
        his = os.environ.get("HYPRLAND_INSTANCE_SIGNATURE")
        runtime_dir = os.environ.get("XDG_RUNTIME_DIR", f"/run/user/{os.getuid()}")

        if his:
            path = os.path.join(runtime_dir, "hypr", his, ".socket2.sock")
            if os.path.exists(path):
                return path

        # Fallback: scan the hypr directory for the first valid socket
        hypr_dir = os.path.join(runtime_dir, "hypr")
        if os.path.isdir(hypr_dir):
            for entry in os.listdir(hypr_dir):
                path = os.path.join(hypr_dir, entry, ".socket2.sock")
                if os.path.exists(path):
                    return path

        return None

    def start_active_window_change_thread(self):
        self.active_window_change_thread = WatchForActiveWindowChange(self)
        self.active_window_change_thread.start()

    def get_all_windows(self) -> list[Window]:
        windows: list[Window] = []
        try:
            # Run the hyprctl command and capture the output
            output = subprocess.check_output(f"{self.command_prefix}hyprctl clients -j", shell=True, text=True, cwd="/").strip()
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

    def get_active_window(self) -> Window:
        try:
            # Run the hyprctl command and capture the output
            output = subprocess.check_output(f"{self.command_prefix}hyprctl activewindow -j", shell=True, text=True, cwd="/").strip()
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
    """Watch for active window changes via Hyprland's IPC event socket.

    Instead of polling ``hyprctl activewindow`` every 200 ms (which spawns a
    new process each time — and ``flatpak-spawn`` + ``xdg-dbus-proxy`` when
    running inside Flatpak), we connect to Hyprland's socket2 and listen for
    ``activewindow>>`` events.  This is pure I/O wait with zero CPU usage
    when the active window doesn't change.

    Falls back to the polling approach only when the socket is unavailable
    (e.g. running outside Hyprland, or socket path unresolvable).
    """

    def __init__(self, hyprland: Hyprland):
        super().__init__(name="WatchForActiveWindowChange", daemon=True)
        self.hyprland = hyprland

    @log.catch
    def run(self) -> None:
        socket_path = self.hyprland._socket_path

        if socket_path and os.path.exists(socket_path):
            log.info(f"Using Hyprland IPC socket for window change events: {socket_path}")
            self._run_socket(socket_path)
        else:
            log.warning("Hyprland IPC socket not found, falling back to polling")
            self._run_polling()

    def _run_socket(self, socket_path: str) -> None:
        """Event-driven: listen on Hyprland's socket2 for activewindow>> events."""
        import time

        while gl.threads_running:
            try:
                sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                sock.settimeout(5.0)
                sock.connect(socket_path)

                buffer = ""
                while gl.threads_running:
                    try:
                        data = sock.recv(4096)
                    except socket.timeout:
                        continue
                    if not data:
                        # Socket closed by compositor — reconnect
                        break

                    buffer += data.decode("utf-8", errors="replace")
                    while "\n" in buffer:
                        line, buffer = buffer.split("\n", 1)
                        if line.startswith("activewindow>>"):
                            # Format: activewindow>>CLASS,TITLE
                            payload = line[len("activewindow>>"):]
                            # Class may not contain commas, but title might
                            parts = payload.split(",", 1)
                            if len(parts) == 2:
                                wm_class, title = parts
                                window = Window(wm_class, title)
                                self.hyprland.window_grabber.on_active_window_changed(window)

                sock.close()
            except OSError as e:
                log.warning(f"Hyprland socket error: {e}, retrying in 2s")
            except Exception as e:
                log.error(f"Unexpected error in Hyprland socket listener: {e}")

            # Brief delay before reconnecting
            time.sleep(2)

    def _run_polling(self) -> None:
        """Fallback: poll hyprctl every 200 ms (legacy behavior)."""
        import time

        last_active_window = self.hyprland.get_active_window()
        while gl.threads_running:
            time.sleep(0.2)
            new_active_window = self.hyprland.get_active_window()
            if new_active_window is None:
                continue
            if new_active_window == last_active_window:
                continue

            last_active_window = new_active_window
            self.hyprland.window_grabber.on_active_window_changed(new_active_window)

