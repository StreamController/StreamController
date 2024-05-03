import os
from src.backend.LockScreenManager.Detectors.Gnome import GnomeLockScreenDetector
from src.backend.LockScreenManager.LockScreenDetector import LockScreenDetector

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

        for controller in gl.deck_manager.deck_controller:
            controller.allow_interaction = not active
            if active:
                controller.screen_saver.show()
            else:
                controller.screen_saver.hide()

        self.locked = active