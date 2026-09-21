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

class HyprlockLockScreenDetector(LockScreenDetector):
    """Track the lock state of a hyprlock session.

    hyprlock is an ext-session-lock client, so Hyprland's lock notifier does
    report it - but that protocol is privileged and the compositor hides it
    from sandboxed clients, which puts it out of reach in the Flatpak.
    hyprlock exposes no IPC of its own; its process runs for exactly as long
    as the session is locked, which is the same signal hypridle configs test
    for with ``pidof hyprlock``.
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
        """Report whether hyprlock is currently running.

        Returns None when pgrep could not answer, so that a failed lookup is
        not mistaken for an unlocked session.
        """
        try:
            returncode = subprocess.run(
                f"{command_prefix}pgrep -x hyprlock",
                shell=True, cwd="/", timeout=5,
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            ).returncode
        except (subprocess.SubprocessError, OSError) as e:
            log.debug(f"hyprlock lookup failed: {e}")
            return None

        # pgrep exits 0 when a process matched and 1 when none did
        if returncode not in (0, 1):
            return None
        return returncode == 0

    @classmethod
    def is_available(cls) -> bool:
        command_prefix = cls.get_command_prefix()
        try:
            return subprocess.run(
                f"{command_prefix}sh -c 'command -v hyprlock'",
                shell=True, cwd="/", timeout=5,
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            ).returncode == 0
        except (subprocess.SubprocessError, OSError) as e:
            log.debug(f"hyprlock lookup failed: {e}")
            return False

    def __init__(self, lock_screen_manager: "LockScreenManager"):
        super().__init__(lock_screen_manager)

        self.command_prefix = self.get_command_prefix()

        threading.Thread(target=self.watch_lock_state, name="HyprlockLockScreenDetector", daemon=True).start()

    @log.catch
    def watch_lock_state(self) -> None:
        log.info("Using hyprlock for lock screen detection")

        locked = self.query_locked(self.command_prefix)

        while gl.threads_running:
            time.sleep(self.POLL_INTERVAL)

            new_locked = self.query_locked(self.command_prefix)
            if new_locked is None or new_locked == locked:
                continue

            locked = new_locked
            # lock() reaches into the deck controllers, which every other
            # detector touches from the main thread
            GLib.idle_add(self.lock_screen_manager.lock, new_locked)
