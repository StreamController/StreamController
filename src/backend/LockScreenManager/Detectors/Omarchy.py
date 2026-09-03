import subprocess
import threading
import time

from gi.repository import GLib

from src.backend.LockScreenManager.LockScreenDetector import LockScreenDetector

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from src.backend.LockScreenManager.LockScreenManager import LockScreenManager

# Import globals first to get IS_MAC
import globals as gl

import gi

if not gl.IS_MAC:
    gi.require_version("Xdp", "1.0")
    from gi.repository import Xdp

from loguru import logger as log

class OmarchyLockScreenDetector(LockScreenDetector):
    """Track the lock state of an Omarchy session.

    Omarchy 4 locks through its own Quickshell session lock rather than
    hyprlock. That is an ordinary ext-session-lock client, so Hyprland's lock
    notifier does report it - but that protocol is privileged and the
    compositor hides it from sandboxed clients, which puts it out of reach in
    the Flatpak. The shell answers ``omarchy-shell lock isLocked`` instead,
    and that can only be polled.
    """

    POLL_INTERVAL = 1

    @staticmethod
    def get_command_prefix() -> str:
        if gl.IS_MAC:
            return ""
        portal = Xdp.Portal.new()
        if portal.running_under_flatpak():
            return "flatpak-spawn --host "
        return ""

    @classmethod
    def query_locked(cls, command_prefix: str) -> bool | None:
        """Ask omarchy-shell whether the session is locked.

        Returns None when the shell gives no usable answer, which is how a
        session that is not Omarchy - or whose shell is not running - is told
        apart from one that is simply unlocked.
        """
        try:
            output = subprocess.check_output(
                f"{command_prefix}omarchy-shell lock isLocked",
                shell=True, text=True, cwd="/", timeout=5,
                stderr=subprocess.DEVNULL
            ).strip()
        except (subprocess.SubprocessError, OSError) as e:
            log.debug(f"omarchy-shell lock query failed: {e}")
            return None

        if output not in ("true", "false"):
            return None
        return output == "true"

    @classmethod
    def is_available(cls) -> bool:
        return cls.query_locked(cls.get_command_prefix()) is not None

    def __init__(self, lock_screen_manager: "LockScreenManager"):
        super().__init__(lock_screen_manager)

        self.command_prefix = self.get_command_prefix()

        threading.Thread(target=self.watch_lock_state, name="OmarchyLockScreenDetector", daemon=True).start()

    @log.catch
    def watch_lock_state(self) -> None:
        log.info("Using omarchy-shell for lock screen detection")

        locked = self.query_locked(self.command_prefix)

        while gl.threads_running:
            time.sleep(self.POLL_INTERVAL)

            new_locked = self.query_locked(self.command_prefix)
            if new_locked is None or new_locked == locked:
                continue

            locked = new_locked
            # lock() reaches into the deck controllers, which every other
            # detector does from the main thread
            GLib.idle_add(self.lock_screen_manager.lock, new_locked)
