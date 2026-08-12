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
# Import python modules
import time
import threading
from loguru import logger as log
from copy import copy

# Import typing
from typing import TYPE_CHECKING

from src.backend.DeckManagement.HelperMethods import get_folder_media_paths
from src.backend.DeckManagement.InputIdentifier import Input
if TYPE_CHECKING:
    from src.backend.DeckManagement.DeckController import DeckController, ControllerKey, Background

class ScreenSaver:
    def __init__(self, deck_controller: "DeckController"):
        self.deck_controller: "DeckController" = deck_controller

        # Init vars
        self.original_inputs = []
        self.original_background: "Background" = None
        self.original_brightness: int = 0

        # Time when last key state changed
        self.last_key_change_time = time.time()

        # Time delay
        self.time_delay = 5

        self.enable: bool = False
        self.showing: bool = False

        self.media_path: str = None
        self.brightness: int = 25
        self.fps: int = 30
        self.loop: bool = True
        self.timer: threading.Timer = None

        # Set to "folder" to cycle through the media files of folder_path instead of
        # showing the single media_path asset
        self.source: str = "file"
        self.folder_path: str = None
        self.rotation_interval: int = 5 # In minutes
        self.rotation_index: int = 0
        self.rotation_timer: threading.Timer = None

    def set_time(self, time_delay: int) -> None:
        time_delay = max(1, time_delay) # Min 1 minute - too small values leading to instant load if the screensaver lead to errors
        if time_delay != self.time_delay:
            log.info(f"Setting screen saver time delay to {time_delay} minutes")
        self.time_delay = time_delay
        if self.timer:
            self.timer.cancel()
        # *60 to go from minuts (how it is stored) to seconds (how the timer needs it)
        self.timer = threading.Timer(time_delay*60, self.on_timer_end)
        self.timer.setDaemon(True)
        self.timer.setName("ScreenSaverTimer")
        if self.enable and not self.showing:
            self.timer.start()

    def set_media_path(self, media_path: str) -> None:
        self.media_path = media_path

        if self.showing:
            self.deck_controller.background.set_from_path(self.get_current_media_path())

    def set_source(self, source: str) -> None:
        if source == self.source:
            return
        self.source = source

        if self.showing:
            # Also stops the rotation when the source is no longer a folder
            self.start_rotation()

    def set_folder_path(self, folder_path: str) -> None:
        if folder_path != self.folder_path:
            self.rotation_index = 0
        self.folder_path = folder_path

    def set_rotation_interval(self, interval: int) -> None:
        interval = max(1, int(interval))
        if interval == self.rotation_interval:
            return
        self.rotation_interval = interval

        if self.showing:
            self.start_rotation()

    def get_current_media_path(self) -> str:
        """The single asset, or the file the folder rotation is currently at."""
        if self.source != "folder":
            return self.media_path

        media_paths = get_folder_media_paths(self.folder_path)
        if len(media_paths) == 0:
            return None
        return media_paths[self.rotation_index % len(media_paths)]

    def apply_media(self) -> None:
        self.deck_controller.background.set_from_path(self.get_current_media_path(), update=True)

        if self.deck_controller.background.video is not None:
            self.deck_controller.background.video.fps = self.fps
            self.deck_controller.background.video.loop = self.loop

    def start_rotation(self) -> None:
        self.stop_rotation()
        if self.source != "folder":
            return

        self.rotation_timer = threading.Timer(self.rotation_interval*60, self.on_rotation_timer_end)
        self.rotation_timer.daemon = True
        self.rotation_timer.name = "ScreenSaverRotationTimer"
        self.rotation_timer.start()

    def stop_rotation(self) -> None:
        if self.rotation_timer is not None:
            self.rotation_timer.cancel()
            self.rotation_timer = None

    def on_rotation_timer_end(self) -> None:
        if not self.showing:
            return

        self.rotation_index += 1
        # Through the media player so the background is only ever touched from its thread
        self.deck_controller.media_player.add_task(self.apply_media, task_label="rotate_screensaver")
        self.start_rotation()

    def set_enable(self, enable: bool) -> None:
        self.enable = enable

        if not self.timer:
            return
        
        # Hide if showing
        if self.showing and not enable:
            self.hide()
        
        # Stop timer if enable == False
        if enable:
            # Start time if not already running
            if not self.timer.is_alive:
                self.timer.start()
        else:
            self.timer.cancel()

    def on_timer_end(self) -> None:
        self.show()

    def show(self):
        log.info("Showing screen saver")
        # Stop timer - in case this method is called manually
        if self.timer:
            self.timer.cancel()
        # Set showing = True - in case this method is called manually
        self.showing = True

        self.original_inputs = self.deck_controller.inputs
        # init_inputs() swaps in a fresh dict on its own - blanking it here first left
        # the media player and tick threads reading an empty dict (issue #535)
        self.deck_controller.init_inputs()

        self.original_background = self.deck_controller.background
        self.original_brightness = self.deck_controller.brightness

        self.deck_controller.set_brightness(self.brightness)

        self.deck_controller.clear()
        self.deck_controller.clear_media_player_tasks()

        # Set background
        self.apply_media()
        self.start_rotation()

        # Release keys
        for key in self.deck_controller.inputs[Input.Key]:
            key.down_start_time = None
            key.press_state = False

    def hide(self):
        log.info("Hiding screen saver")
        self.stop_rotation()
        self.original_inputs.clear()
        self.deck_controller.clear() # Ensures that the first image visable is from the page not the screensaver if the brightness on the saver is 0
        self.showing = False
        if self.deck_controller.active_page:
            self.deck_controller.load_page(
                self.deck_controller.active_page,
                allow_reload=True,
                force_background_reload=True,
            )
        else:
            self.deck_controller.load_default_page()
        self.set_time(self.time_delay)

    def on_key_change(self):
        self.last_key_change_time = time.time()
        if self.showing:
            self.hide()
        else:
            self.set_time(self.time_delay)

    def set_brightness(self, brightness: int) -> None:
        self.brightness = int(brightness)

        if self.showing:
            self.deck_controller.set_brightness(self.brightness)

    def set_fps(self, fps: int) -> None:
        self.fps = fps
        if not self.showing:
            return
        if self.deck_controller.background.video is not None:
            self.deck_controller.background.video.fps = fps

    def set_loop(self, loop: bool) -> None:
        self.loop = loop
        if not self.showing:
            return
        if self.deck_controller.background.video is not None:
            self.deck_controller.background.video.loop = loop
