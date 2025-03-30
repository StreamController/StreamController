import threading
import time

import wayland
from os import getenv
import globals as gl
from loguru import logger as log

from src.Signals.Signals import AppQuit
from src.backend.Wayland import WaylandSignals


class Wayland:
    def __on_wl_registry_global(self, name, interface, version):
        if interface == "hyprland_lock_notifier_v1":
            log.debug("Hyprland lock notifier found, hooking...")
            wayland.wl_registry.bind(name, interface, version, name)
            wayland.hyprland_lock_notifier_v1.get_lock_notification()

    def __on_lock(self):
        gl.signal_manager.trigger_signal(WaylandSignals.HyprlandLock)

    def __on_unlock(self):
        gl.signal_manager.trigger_signal(WaylandSignals.HyprlandUnlock)

    def __on_quit(self):
        self.__quit = True

    def __tick_wayland_messages_threaded(self):
        while not self.__quit:
            wayland.process_messages()
            time.sleep(self.__TICK_DELAY)

    def __init__(self):
        self.__quit = False
        self.__TICK_DELAY = 0.1
        if not getenv("WAYLAND_DISPLAY", False):
            raise(EnvironmentError("Attempted to initialize Wayland when WAYLAND_DISPLAY is not set"))
        wayland.initialise(True)

        gl.signal_manager.connect_signal(AppQuit, self.__on_quit)

        wayland.wl_registry.events.global_ += self.__on_wl_registry_global
        wayland.hyprland_lock_notification_v1.events.locked += self.__on_lock
        wayland.hyprland_lock_notification_v1.events.unlocked += self.__on_unlock

        wayland.wl_display.get_registry()

        threading.Thread(target=self.__tick_wayland_messages_threaded, name="tick_wayland_messages_threaded").start()