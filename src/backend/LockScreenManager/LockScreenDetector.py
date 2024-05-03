from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from src.backend.LockScreenManager.LockScreenManager import LockScreenManager

class LockScreenDetector:
    def __init__(self, lock_screen_manager: "LockScreenManager"):
        self.lock_screen_manager: "LockScreenManager" = lock_screen_manager