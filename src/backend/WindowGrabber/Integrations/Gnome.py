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

# Import globals first to get IS_MAC
import globals as gl

import gi
from gi.repository import Gio

# Import typing
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from src.backend.WindowGrabber.WindowGrabber import WindowGrabber

class Gnome(Integration):
    DBUS_NAME = "org.gnome.Shell"
    DBUS_PATH = "/org/gnome/Shell/Extensions/StreamController"
    DBUS_INTERFACE = "org.gnome.Shell.Extensions.StreamController"

    def __init__(self, window_grabber: "WindowGrabber"):
        super().__init__(window_grabber=window_grabber)

        self.proxy = None
        if not gl.IS_MAC:
            self.connect_dbus()

    def install_extension(self) -> None:
        uuid = ["streamcontroller@core447.com"]
        installed_extensions = gl.gnome_extensions.get_installed_extensions()

        if uuid in installed_extensions:
            return
        
        gl.gnome_extensions.request_installation(uuid)


    def connect_dbus(self) -> None:
        if gl.IS_MAC:
            return
        try:
            self.proxy = Gio.DBusProxy.new_for_bus_sync(
                Gio.BusType.SESSION,
                Gio.DBusProxyFlags.DO_NOT_LOAD_PROPERTIES | Gio.DBusProxyFlags.DO_NOT_AUTO_START,
                None,
                self.DBUS_NAME,
                self.DBUS_PATH,
                self.DBUS_INTERFACE,
                None
            )
            self.proxy.connect("g-signal", self.on_g_signal)
        except Exception as e:
            log.error(f"Failed to connect to D-Bus: {e}")

    def on_g_signal(self, proxy, sender_name: str, signal_name: str, parameters) -> None:
        if signal_name == "FocusedWindowChanged":
            self.on_window_changed(parameters.unpack()[0])

    def call_method(self, method_name: str) -> str:
        result = self.proxy.call_sync(method_name, None, Gio.DBusCallFlags.NONE, -1, None)
        return result.unpack()[0]

    def on_window_changed(self, answer: str) -> None:
        answer = json.loads(answer)
        window = Window(answer.get("wm_class"), answer.get("title"))
        self.window_grabber.on_active_window_changed(window=window)
        
    def get_all_windows(self) -> list[Window]:
        if not self.get_is_connected():
            return []
        
        try:
            answer = json.loads(self.call_method("GetAllWindows"))
        except:
            return []
        windows: list[Window] = []
        
        for window in answer:
            wm_class = window.get("wm_class")
            title = window.get("title")
            windows.append(Window(wm_class, title))

        return windows
    
    def get_active_window (self) -> Window:
        if not self.get_is_connected():
            return None
        try:
            answer = json.loads(self.call_method("GetFocusedWindow"))
        except:
            return None
        wm_class = answer.get("wm_class")
        title = answer.get("title") 
        return Window(wm_class, title)
    
    def get_is_connected(self) -> bool:
        return self.proxy is not None and self.proxy.get_name_owner() is not None
