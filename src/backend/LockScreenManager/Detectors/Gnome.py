from src.backend.LockScreenManager.LockScreenDetector import LockScreenDetector

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from src.backend.LockScreenManager.LockScreenManager import LockScreenManager

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
        # Use the D-Bus MainLoop with glib integration
        dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)

        try:
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
        