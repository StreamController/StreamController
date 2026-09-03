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
import os
import threading
from src.backend.LockScreenManager.Detectors.Gnome import GnomeLockScreenDetector
from src.backend.LockScreenManager.Detectors.Cinnamon import CinnamonLockScreenDetector
from src.backend.LockScreenManager.Detectors.KDE import KDELockScreenDetector
from src.backend.LockScreenManager.Detectors.Hyprland import HyprlandLockScreenDetector
from src.backend.LockScreenManager.Detectors.Omarchy import OmarchyLockScreenDetector
from src.backend.LockScreenManager.Detectors.Logind import LogindLockScreenDetector
from src.backend.LockScreenManager.LockScreenDetector import LockScreenDetector
from loguru import logger as log

import globals as gl

class LockScreenManager:
    def __init__(self):
        self.locked = False

        threading.Thread(target=self.setup, daemon=True).start() # Run in separate thread incase something gets stuck

    @log.catch
    def setup(self):
        env = self.get_active_environment()

        # Hyprland uses the Wayland lock notifier protocol directly
        if env == "hyprland":
            if self.wait_for_hyprland_lock_notifier():
                self.detector = HyprlandLockScreenDetector(self)
                return

            # The notifier covers every ext-session-lock client, hyprlock and
            # Omarchy's Quickshell lock alike, but the compositor withholds it
            # from sandboxed clients - so under Flatpak an Omarchy session has
            # to be asked about its own lock instead.
            if OmarchyLockScreenDetector.is_available():
                self.detector = OmarchyLockScreenDetector(self)
                return

            self.detector = HyprlandLockScreenDetector(self)
            return

        # Try logind
        try:
            self.detector = LogindLockScreenDetector(self)
            return
        except Exception as e:
            log.debug(f"Logind lock detection not available: {e}")

        # Fall back to DE-specific DBus detectors
        if env == "gnome":
            self.detector = GnomeLockScreenDetector(self)
        elif env == "x-cinnamon":
            self.detector = CinnamonLockScreenDetector(self)
        elif env == "kde":
            self.detector = KDELockScreenDetector(self)

    @log.catch
    def wait_for_hyprland_lock_notifier(self, timeout: float = 2) -> bool:
        """Wait for the registry to report Hyprland's lock notifier.

        The globals arrive on the Wayland tick thread shortly after startup, so
        the answer is not in yet by the time this runs.
        """
        wayland = getattr(gl, "wayland", None)
        if wayland is None:
            return False
        return wayland.lock_notifier_found.wait(timeout)

    @log.catch
    def get_active_environment(self) -> str:
        desktop = os.getenv("XDG_CURRENT_DESKTOP")
        if desktop is None:
            return
        return desktop.lower()

    @log.catch
    def lock(self, active):
        gl.screen_locked = active

        if active:
            settings = gl.settings_manager.get_app_settings()
            if not settings.get("system", {}).get("lock-on-lock-screen", True):
                return

        if active == self.locked:
            return
        
        log.info(f"Locking screen: {active}")

        for controller in gl.deck_manager.deck_controller:
            controller.allow_interaction = not active
            if active:
                controller.screen_saver.show()
            else:
                controller.screen_saver.hide()

        self.locked = active
