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
from loguru import logger as log

class GnomeExtensions:
    def __init__(self):
        self.bus = None
        self.proxy = None
        self.interface = None
        self.connect_dbus()

    def connect_dbus(self) -> None:
        try:
            self.bus = dbus.SessionBus()
            self.proxy = self.bus.get_object("org.gnome.Shell", "/org/gnome/Shell")
            self.interface = dbus.Interface(self.proxy, "org.gnome.Shell.Extensions")
        except dbus.exceptions.DBusException as e:
            log.error(f"Failed to connect to D-Bus: {e}")
            pass

    def get_is_connected(self) -> bool:
        return None not in (self.bus, self.proxy, self.interface)
    
    def get_installed_extensions(self) -> list[str]:
        extensions: list[str] = []
        if not self.get_is_connected(): return extensions

        for extension in self.interface.ListExtensions():
            extensions.append(extension)
        return extensions

    def request_installation(self, uuid: str) -> bool:
        if not self.get_is_connected(): return False
        response = self.interface.InstallRemoteExtension(uuid)
        return True if response == "successful" else False