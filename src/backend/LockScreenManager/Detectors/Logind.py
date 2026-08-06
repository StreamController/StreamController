from src.backend.LockScreenManager.LockScreenDetector import LockScreenDetector

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from src.backend.LockScreenManager.LockScreenManager import LockScreenManager

import os

# Import globals first to get IS_MAC
import globals as gl

if not gl.IS_MAC:
    import dbus

from loguru import logger as log

class LogindLockScreenDetector(LockScreenDetector):
    def __init__(self, lock_screen_manager: "LockScreenManager"):
        self.lock_screen_manager: "LockScreenManager" = lock_screen_manager

        self.setup_dbus()

    def on_lock(self):
        self.lock_screen_manager.lock(True)

    def on_unlock(self):
        self.lock_screen_manager.lock(False)

    def setup_dbus(self):
        if gl.IS_MAC:
            return

        # Use the D-Bus MainLoop with glib integration
        dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)

        # Connect to the System Bus
        bus = dbus.SystemBus()

        # Resolve the session path for the current user session
        session_path = self._resolve_session_path(bus)

        log.info(f"Logind lock detector active ({session_path})")

        session_obj = bus.get_object("org.freedesktop.login1", session_path)
        session_obj.connect_to_signal(
            "Lock", self.on_lock,
            dbus_interface="org.freedesktop.login1.Session"
        )
        session_obj.connect_to_signal(
            "Unlock", self.on_unlock,
            dbus_interface="org.freedesktop.login1.Session"
        )

    def _resolve_session_path(self, bus) -> str:
        manager = bus.get_object("org.freedesktop.login1", "/org/freedesktop/login1")
        manager_iface = dbus.Interface(manager, "org.freedesktop.login1.Manager")

        session_id = os.environ.get("XDG_SESSION_ID")
        if session_id:
            try:
                return manager_iface.GetSession(session_id)
            except dbus.DBusException as e:
                log.warning(f"Failed to resolve logind session via XDG_SESSION_ID={session_id}: {e}")

        return manager_iface.GetSessionByPID(os.getpid())
