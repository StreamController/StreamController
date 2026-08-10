from src.backend.LockScreenManager.LockScreenDetector import LockScreenDetector

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from src.backend.LockScreenManager.LockScreenManager import LockScreenManager

import os

from gi.repository import Gio

# Import globals first to get IS_MAC
import globals as gl

if not gl.IS_MAC:
    import dbus

from loguru import logger as log

class LogindLockScreenDetector(LockScreenDetector):
    def __init__(self, lock_screen_manager: "LockScreenManager"):
        self.lock_screen_manager: "LockScreenManager" = lock_screen_manager

        self.setup_dbus()

    def on_lock(self, *_args):
        self.lock_screen_manager.lock(True)

    def on_unlock(self, *_args):
        self.lock_screen_manager.lock(False)

    def setup_dbus(self):
        if gl.IS_MAC:
            return

        # Resolving the session path only needs blocking calls, which
        # dbus-python supports without a main loop attached.
        bus = dbus.SystemBus()

        # Resolve the session path for the current user session
        session_path = self._resolve_session_path(bus)

        log.info(f"Logind lock detector active ({session_path})")

        # This runs on the LockScreenManager setup thread, and dbus-python's
        # GLib main loop integration is not thread safe, so signals are
        # subscribed to via GDBus (Gio) instead of connect_to_signal(), which
        # would require installing that main loop.
        self.bus = Gio.bus_get_sync(Gio.BusType.SYSTEM, None)
        self.lock_subscription_id = self.bus.signal_subscribe(
            "org.freedesktop.login1",
            "org.freedesktop.login1.Session",
            "Lock",
            session_path,
            None,
            Gio.DBusSignalFlags.NONE,
            self.on_lock
        )
        self.unlock_subscription_id = self.bus.signal_subscribe(
            "org.freedesktop.login1",
            "org.freedesktop.login1.Session",
            "Unlock",
            session_path,
            None,
            Gio.DBusSignalFlags.NONE,
            self.on_unlock
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
