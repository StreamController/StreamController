from src.backend.LockScreenManager.LockScreenDetector import LockScreenDetector
import globals as gl
from src.backend.Wayland.WaylandSignals import HyprlandLock, HyprlandUnlock

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.backend.LockScreenManager.LockScreenManager import LockScreenManager

class HyprlandLockScreenDetector(LockScreenDetector):
    def __lock(self):
        self.lock_screen_manager.lock(True)

    def __unlock(self):
        self.lock_screen_manager.lock(False)

    def __init__(self, lock_screen_manager: "LockScreenManager"):
        super().__init__(lock_screen_manager)

        gl.signal_manager.connect_signal(signal=HyprlandLock, callback=self.__lock)

        gl.signal_manager.connect_signal(signal=HyprlandUnlock, callback=self.__unlock)