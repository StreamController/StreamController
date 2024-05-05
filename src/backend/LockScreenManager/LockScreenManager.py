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
from src.backend.LockScreenManager.Detectors.Gnome import GnomeLockScreenDetector
from src.backend.LockScreenManager.LockScreenDetector import LockScreenDetector
from loguru import logger as log

import globals as gl

class LockScreenManager:
    def __init__(self):
        self.locked = False

        env = self.get_active_environment()
        if env == "gnome":
            self.detector = GnomeLockScreenDetector(self)

    def get_active_environment(self) -> str:
        desktop = os.getenv("XDG_CURRENT_DESKTOP")
        if desktop is None:
            return
        return desktop.lower()

    def lock(self, active):
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