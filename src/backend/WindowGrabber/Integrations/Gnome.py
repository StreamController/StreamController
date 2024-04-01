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

import dbus
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

class Gnome(Integration):
    def __init__(self, window_grabber: "WindowGrabber"):
        super().__init__(window_grabber=window_grabber)

        self.bus: dbus.Bus = None
        self.proxy =  None
        self.interface = None
        self.install_extension()
        self.connect_dbus()

    def install_extension(self) -> None:
        uuid = ["streamcontroller@core447.com"]
        installed_extensions = gl.gnome_extensions.get_installed_extensions()

        if uuid in installed_extensions:
            return
        
        gl.gnome_extensions.request_installation(uuid)


    def connect_dbus(self) -> None:
        try:
            self.bus = dbus.SessionBus()
            self.proxy = self.bus.get_object("org.gnome.Shell", "/org/gnome/Shell/Extensions/StreamController")
            self.interface = dbus.Interface(self.proxy, "org.gnome.Shell.Extensions.StreamController")
            self.interface.connect_to_signal("FocusedWindowChanged", self.on_window_changed)
        except dbus.exceptions.DBusException as e:
            log.error(f"Failed to connect to D-Bus: {e}")
            pass


    def on_window_changed(self, answer: str) -> None:
        answer = json.loads(answer)
        window = Window(answer.get("wm_class"), answer.get("title"))
        self.window_grabber.on_active_window_changed(window=window)
        
    def get_all_windows(self) -> list[Window]:
        if not self.get_is_connected():
            return []
        
        try:
            answer = json.loads(self.interface.GetAllWindows())
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
            answer = json.loads(self.interface.GetFocusedWindow())
        except:
            return None
        wm_class = answer.get("wm_class")
        title = answer.get("title") 
        return Window(wm_class, title)
    
    def get_is_connected(self) -> bool:
        return None not in (self.bus, self.proxy, self.interface)