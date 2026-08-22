"""
Author: M-Pistillucci
Year: 2026

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

class MangoWM(Integration):
    def __init__(self, window_grabber: "WindowGrabber"):
        super().__init__(window_grabber=window_grabber)

        self.command_prefix = ""
        if not gl.IS_MAC:
            portal = Xdp.Portal.new()
            if portal.running_under_flatpak():
                self.command_prefix = "flatpak-spawn --host "

        self._socket_path = self._find_socket_path()
        self.start_active_window_change_thread()

    def _find_socket_path(self) -> str | None:
        """Find the MangoWM IPC event socket.

        Returns the path to the socket, or None if not found.
        """
        his = os.environ.get("MANGO_INSTANCE_SIGNATURE")
        if his and os.path.exists(his):
            return his

        # Fallback
        runtime_dir = os.environ.get("XDG_RUNTIME_DIR", f"/run/user/{os.getuid()}")
        if os.path.exists(runtime_dir):
                for file in os.listdir(runtime_dir):
                    if file.startswith("mango-") and file.endswith(".sock"):
                        socket_path = os.path.join(runtime_dir, file)
                        return socket_path

        return None

    def start_active_window_change_thread(self):
        self.active_window_change_thread = WatchForActiveWindowChange(self)
        self.active_window_change_thread.start()

    def get_all_windows(self) -> list[Window]:
        windows: list[Window] = []
        try:
            # Run the mmsg get command and capture the output
            output = subprocess.check_output(f"{self.command_prefix}mmsg get all-clients", shell=True, text=True, cwd="/").strip()
            # Parse the JSON output into a Python list
            clients = json.loads(output)

            for client in clients:
                if "appid" in client and "title" in client:
                    windows.append(Window(client["appid"], client["title"]))

        except subprocess.CalledProcessError as e:
            log.error(f"An error occurred while running mmsg get: {e}")
        except json.JSONDecodeError as e:
            log.error(f"Failed to parse JSON: {e}")

        return windows

    def get_active_window(self) -> Window | None:
        try:
            # Run the mmsg get and capture the output
            output = subprocess.check_output(f"{self.command_prefix}mmsg get focusing-client", shell=True, text=True, cwd="/").strip()
            # Parse the JSON output into a Python list
            client = json.loads(output)

            if "appid" in client and "title" in client:
                return Window(client["appid"], client["title"])
        except subprocess.CalledProcessError as e:
            log.error(f"An error occurred while running mmsg get: {e}")
        except json.JSONDecodeError as e:
            log.error(f"Failed to parse JSON: {e}")

        return None


class WatchForActiveWindowChange(threading.Thread):
    """Watch for active window changes via MangoWM's IPC event socket.

    Instead of polling ``mmsg get focusing-client`` every 200 ms (which spawns a
    new process each time — and ``flatpak-spawn`` + ``xdg-dbus-proxy`` when
    running inside Flatpak), we connect to MangoWM's socket and listen for
    ``focusing-client`` events.  This is pure I/O wait with zero CPU usage
    when the active window doesn't change.

    Falls back to the polling approach only when the socket is unavailable
    (e.g. running outside MangoWM, or socket path unresolvable).
    """

    def __init__(self, mangowm: MangoWM):
        super().__init__(name="WatchForActiveWindowChange", daemon=True)
        self.mangowm = mangowm

    @log.catch
    def run(self) -> None:
        socket_path = self.mangowm._socket_path

        if socket_path and os.path.exists(socket_path):
            log.info(f"Using MangoWM IPC socket for window change events: {socket_path}")
            self._run_socket(socket_path)
        else:
            log.warning("MangoWM IPC socket not found, falling back to polling")
            self._run_polling()

    def _run_socket(self, socket_path: str) -> None:
        """Event-driven: listen on MangoWM's socket for activewindow>> events."""
        import time

        def extract_window_info(json_str: str) -> tuple[str | None, str | None]:
                try:
                    data = json.loads(json_str)
                    app_id = data.get("appid")
                    title = data.get("title")

                    return app_id, title
                except json.JSONDecodeError:
                    return None, None

        while gl.threads_running:
            try:
                sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                sock.settimeout(5.0)
                sock.connect(socket_path)

                buffer = ""
                sock.sendall(b"watch focusing-client\n")
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
                        line = line.strip()
                        if line:

                            # Format: focusing-client -> CLASS,TITLE
                            wm_class,title = extract_window_info(line)
                            if wm_class:
                                window = Window(wm_class, title or "")

                                if hasattr(self.mangowm, "window_grabber") and self.mangowm.window_grabber:
                                    try:
                                        self.mangowm.window_grabber.on_active_window_changed(window)
                                    except AttributeError as e:
                                        log.warning(f"WindowGrabber not initialized yet: {e}")


                sock.close()
            except OSError as e:
                log.warning(f"MangoWM socket error: {e}, retrying in 2s")
            except Exception as e:
                log.error(f"Unexpected error in MangoWM socket listener: {e}")

            # Brief delay before reconnecting
            time.sleep(2)

    def _run_polling(self) -> None:
        """Fallback: poll mmsg get focusing-client every 200 ms (legacy behavior)."""
        import time

        last_active_window = self.mangowm.get_active_window()
        while gl.threads_running:
            time.sleep(0.2)
            new_active_window = self.mangowm.get_active_window()
            if new_active_window is None:
                continue
            if new_active_window == last_active_window:
                continue

            last_active_window = new_active_window
            if hasattr(self.mangowm, "window_grabber") and self.mangowm.window_grabber:
                try:
                    self.mangowm.window_grabber.on_active_window_changed(new_active_window)
                except AttributeError as e:
                    log.warning(f"WindowGrabber not initialized yet: {e}")
