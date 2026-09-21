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

import threading
import time
import select

from src.backend.WindowGrabber.Integration import Integration
from src.backend.WindowGrabber.Window import Window

# Import globals first to get IS_MAC
import globals as gl

from loguru import logger as log

try:
    from Xlib import X, display as xlib_display
    from Xlib.error import XError
    HAS_XLIB = True
except ImportError:
    HAS_XLIB = False

# Import typing
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from src.backend.WindowGrabber.WindowGrabber import WindowGrabber

_NET_ACTIVE_WINDOW = "_NET_ACTIVE_WINDOW"
_NET_CLIENT_LIST = "_NET_CLIENT_LIST"
_NET_WM_NAME = "_NET_WM_NAME"
_WM_NAME = "WM_NAME"
_WM_CLASS = "WM_CLASS"


class X11(Integration):
    def __init__(self, window_grabber: "WindowGrabber"):
        super().__init__(window_grabber=window_grabber)

        self.display: xlib_display.Display | None = None
        self.root = None
        self._atoms: dict[str, int] = {}

        if HAS_XLIB:
            self._connect()
        else:
            log.warning("X11: python-xlib is not available; active-window tracking is disabled")

        if self.display is not None:
            self.start_active_window_change_thread()
        else:
            # No fallback polling: without a working X connection, xprop-style
            # polling could never succeed and would only reproduce the CPU
            # churn this integration is designed to avoid.
            log.warning("X11: could not open an X connection; active-window tracking is disabled")

    def _connect(self) -> None:
        try:
            self.display = xlib_display.Display()
            self.root = self.display.screen().root
            self._atoms = {
                name: self.display.intern_atom(name)
                for name in (_NET_ACTIVE_WINDOW, _NET_CLIENT_LIST, _NET_WM_NAME, _WM_NAME, _WM_CLASS)
            }
        except Exception as e:
            log.warning(f"X11: could not open X display: {e}")
            self.display = None

    def start_active_window_change_thread(self):
        self.active_window_change_thread = WatchForActiveWindowChange(self)
        self.active_window_change_thread.start()

    # ── property reads over the shared X connection (no subprocesses) ──

    def _get_property(self, window_id: int, atom_name: str):
        try:
            win = self.display.create_resource_object("window", window_id)
            prop = win.get_full_property(self._atoms[atom_name], X.AnyPropertyType)
            return prop
        except Exception:
            return None

    def get_active_window(self) -> Window | None:
        # _NET_ACTIVE_WINDOW is a root-window property (EWMH)
        try:
            prop = self.root.get_full_property(self._atoms[_NET_ACTIVE_WINDOW], X.AnyPropertyType)
        except Exception:
            return None
        if prop is None or len(prop.value) == 0:
            return None
        for window_id in prop.value:
            if window_id == 0:
                continue
            wm_class = self.get_class(window_id)
            title = self.get_title(window_id)
            if None in (wm_class, title):
                return None
            return Window(wm_class, title)
        return None

    def get_title(self, window_id: int) -> str | None:
        for atom_name in (_NET_WM_NAME, _WM_NAME):
            prop = self._get_property(window_id, atom_name)
            if prop is not None and len(prop.value) > 0:
                return bytes(prop.value).decode("utf-8", errors="replace")
        return None

    def get_class(self, window_id: int) -> str | None:
        prop = self._get_property(window_id, _WM_CLASS)
        if prop is None or len(prop.value) == 0:
            return None
        # WM_CLASS is two NUL-separated strings: instance\0class\0
        parts = bytes(prop.value).split(b"\0")
        if len(parts) < 2:
            return None
        return parts[1].decode("utf-8", errors="replace")

    def get_all_windows(self) -> list[Window]:
        try:
            prop = self.root.get_full_property(self._atoms[_NET_CLIENT_LIST], X.AnyPropertyType)
        except Exception:
            return []
        if prop is None:
            return []

        windows: list[Window] = []
        for window_id in prop.value:
            title = self.get_title(window_id)
            class_name = self.get_class(window_id)
            if None in (title, class_name):
                continue
            windows.append(Window(class_name, title))
        return windows


class WatchForActiveWindowChange(threading.Thread):
    """Event-driven X11 watcher (mirrors the Hyprland socket watcher from PR #580).

    Waits for PropertyNotify of _NET_ACTIVE_WINDOW on the root window and reads
    title/class directly over the sandbox's X connection — no subprocesses, no
    flatpak-spawn, no D-Bus, zero CPU while the active window does not change.
    """

    def __init__(self, x11: X11):
        super().__init__(name="WatchForActiveWindowChange", daemon=True)
        self.x11 = x11
        self.last_active_window = x11.get_active_window()

    @log.catch
    def run(self) -> None:
        x = self.x11
        try:
            x.root.change_attributes(event_mask=X.PropertyChangeMask)
            x.display.flush()  # python-xlib buffers requests; without the flush
            # the mask is never registered and no PropertyNotify ever arrives
        except XError:
            log.error("X11: cannot select property events on root; watcher disabled")
            return
        display_fd = x.display.fileno()

        while gl.threads_running:
            try:
                ready, _, _ = select.select([display_fd], [], [], 1.0)
                if not ready:
                    continue
                while x.display.pending_events() and gl.threads_running:
                    event = x.display.next_event()
                    if event.type != X.PropertyNotify:
                        continue
                    if event.atom != x._atoms[_NET_ACTIVE_WINDOW]:
                        continue
                    new_window = x.get_active_window()
                    if new_window is None:
                        continue
                    if new_window == self.last_active_window:
                        continue
                    self.last_active_window = new_window
                    x.window_grabber.on_active_window_changed(new_window)
            except Exception as e:
                # Never let a transient error silently kill the watcher
                log.warning(f"X11: watcher error ({e}); continuing")
                time.sleep(0.5)
