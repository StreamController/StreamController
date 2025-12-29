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
from src.backend.LockScreenManager.LockScreenDetector import LockScreenDetector

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from src.backend.LockScreenManager.LockScreenManager import LockScreenManager

# Import globals first to get IS_MAC
import globals as gl

if not gl.IS_MAC:
    import dbus

from loguru import logger as log

class GnomeLockScreenDetector(LockScreenDetector):
    def __init__(self, lock_screen_manager: "LockScreenManager"):
        self.lock_screen_manager: "LockScreenManager" = lock_screen_manager

        self.setup_dbus()

    def screen_saver_active_changed(self, active):
        active = True if active == 1 else False

        self.lock_screen_manager.lock(active)

    def setup_dbus(self):
        if gl.IS_MAC:
            return
        try:
            # Use the D-Bus MainLoop with glib integration
            dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)

            # Connect to the Session Bus
            bus = dbus.SessionBus()

            # Define the signal to listen to
            bus.add_signal_receiver(
                self.screen_saver_active_changed,
                dbus_interface="org.gnome.ScreenSaver",
                signal_name="ActiveChanged",
                path="/org/gnome/ScreenSaver"
            )
        except Exception as e:
            log.error(f"Failed to connect to D-Bus: {e}")
