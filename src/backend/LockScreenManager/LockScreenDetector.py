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
from gi.repository import Gio

from loguru import logger as log

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from src.backend.LockScreenManager.LockScreenManager import LockScreenManager

class LockScreenDetector:
    # Subclasses assign self.lock_screen_manager without calling super().__init__()
    bus: Gio.DBusConnection = None
    subscription_id: int = None

    def __init__(self, lock_screen_manager: "LockScreenManager"):
        self.lock_screen_manager: "LockScreenManager" = lock_screen_manager

    def subscribe_to_screen_saver(self, interface: str, path: str) -> None:
        """
        Watch a screen saver's ActiveChanged signal.

        GDBus is used rather than dbus-python because this runs on the
        LockScreenManager setup thread, and dbus-python's GLib main loop
        integration is not thread safe. The signal is delivered on the main
        context either way.
        """
        try:
            self.bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
            self.subscription_id = self.bus.signal_subscribe(
                None,
                interface,
                "ActiveChanged",
                path,
                None,
                Gio.DBusSignalFlags.NONE,
                self.__on_active_changed
            )
        except Exception as e:
            log.error(f"Failed to connect to D-Bus: {e}")

    def __on_active_changed(self, connection, sender_name: str, object_path: str,
                            interface_name: str, signal_name: str, parameters) -> None:
        self.screen_saver_active_changed(parameters.unpack()[0])
