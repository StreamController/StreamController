"""
Author: Core447
Year: 2023

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
any later version.

This programm comes with ABSOLUTELY NO WARRANTY!

You should have received a copy of the GNU General Public License
along with this program. If not, see <https://www.gnu.org/licenses/>.
"""
import statistics
import threading
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING, ClassVar, cast

from StreamDeck.Devices import StreamDeck
from gi.repository import GLib
from loguru import logger as log

from src.backend.DeckManagement.InputIdentifier import Input
from src.backend.PageManagement.Page import Page

import globals as gl

if TYPE_CHECKING:
    from src.backend.DeckManagement.DeckController import (
        ControllerDial,
        ControllerKey,
        DeckController,
    )
    from src.windows.mainWindow.elements.DeckStackChild import DeckStackChild


@dataclass
class MediaPlayerTask:
    deck_controller: "DeckController"
    page: Page
    _callable: callable
    args: tuple
    kwargs: dict

    def run(self):
        self._callable(*self.args, **self.kwargs)

@dataclass
class MediaPlayerSetTouchscreenImageTask:
    deck_controller: "DeckController"
    page: Page
    native_image: bytes

    n_failed_in_row: ClassVar[dict] = {}

    def run(self):
        if not self.deck_controller.deck.is_touch():
            return
        try:
            touchscreen_size = self.deck_controller.get_touchscreen_image_size()
            self.deck_controller.deck.set_touchscreen_image(self.native_image, x_pos=0, y_pos=0, width=touchscreen_size[0], height=touchscreen_size[1]) # Maybe avoid to always merge the dial images before applying it
            self.native_image = None
            del self.native_image
            MediaPlayerSetTouchscreenImageTask.n_failed_in_row = 0
        except StreamDeck.TransportError as e:
            log.error(f"Failed to set deck touchscreen image. Error: {e}")
            MediaPlayerSetTouchscreenImageTask.n_failed_in_row += 1
            if MediaPlayerSetTouchscreenImageTask.n_failed_in_row > 5:
                log.debug(f"Failed to set touchscreen image for 5 times in a row for deck {self.deck_controller.serial_number()}. Removing controller")
                
                
                self.deck_controller.deck.close()
                self.deck_controller.media_player.running = False # Set stop flag - otherwise remove_controller will wait until this task is done, which it never will because it waits
                gl.deck_manager.remove_controller(self.deck_controller)

                gl.deck_manager.connect_new_decks()

@dataclass
class MediaPlayerSetImageTask:
    deck_controller: "DeckController"
    page: Page
    key_index: int
    native_image: bytes

    n_failed_in_row: ClassVar[dict] = {}

    def run(self):
        try:
            self.deck_controller.deck.set_key_image(self.key_index, self.native_image)
            self.native_image = None
            del self.native_image
            MediaPlayerSetImageTask.n_failed_in_row[self.deck_controller.serial_number()] = 0
        except StreamDeck.TransportError as e:
            log.error(f"Failed to set deck key image. Error: {e}")

            beta_resume = gl.settings_manager.get_app_settings().get("system", {}).get("beta-resume-mode", True)
            if beta_resume:
                return

            MediaPlayerSetImageTask.n_failed_in_row[self.deck_controller.serial_number()] += 1
            if MediaPlayerSetImageTask.n_failed_in_row[self.deck_controller.serial_number()] > 5:
                log.debug(f"Failed to set key_image for 5 times in a row for deck {self.deck_controller.serial_number()}. Removing controller")
                
                
                self.deck_controller.deck.close()
                self.deck_controller.media_player.running = False # Set stop flag - otherwise remove_controller will wait until this task is done, which it never will because it waits
                gl.deck_manager.remove_controller(self.deck_controller)

                gl.deck_manager.connect_new_decks()


class MediaPlayerThread(threading.Thread):
    def __init__(self, deck_controller: "DeckController"):
        super().__init__(name="MediaPlayerThread", daemon=True)
        self.deck_controller: DeckController = deck_controller
        self.FPS = 30 # Max refresh rate of the internal displays

        self.running = False
        self.media_ticks = 0

        self.pause = False
        self._stop = False

        self.tasks: list[MediaPlayerTask] = []
        self.image_tasks = {}
        self.touchscreen_task = None
        self._wake_event = threading.Event()

        self.fps: list[float] = []
        self.old_warning_state = False

        self.show_fps_warnings = gl.settings_manager.get_app_settings().get("warnings", {}).get("enable-fps-warnings", True)

    # @log.catch
    def run(self):
        self.running = True

        while True:
            start = time.time()

            # self.check_connection()

            if not self.pause:
                has_bg_video = False

                if self.deck_controller.background.video is not None:
                    if self.deck_controller.background.video.page is self.deck_controller.active_page:
                        has_bg_video = True
                        # There is a background video
                        video_each_nth_frame = self.FPS // self.deck_controller.background.video.fps
                        if self.media_ticks % video_each_nth_frame == 0:
                            self.deck_controller.background.update_tiles()

                # Only iterate keys if there is animated content to update
                if has_bg_video or self._needs_key_ticks():
                    #TODO: generalize
                    for key in self.deck_controller.inputs[Input.Key]:
                        cast("ControllerKey", key).on_media_player_tick()

                    for dial in self.deck_controller.inputs[Input.Dial]:
                        cast("ControllerDial", dial).on_media_player_tick()
                    # self.deck_controller.update_all_inputs()

                # Perform media player tasks
                self.perform_media_player_tasks()

            self.media_ticks += 1

            end = time.time()

            # Use low FPS when idle (no animated content, no pending tasks)
            has_pending = bool(self.tasks or self.image_tasks or self.touchscreen_task)
            if has_pending or has_bg_video or getattr(self, '_cached_needs_ticks', False):
                target_fps = self.FPS
            else:
                target_fps = 2  # Idle: just check for new tasks occasionally

            self.append_fps(1 / (end - start))
            self.update_low_fps_warning()
            wait = max(0, 1/target_fps - (end - start))
            if target_fps < self.FPS:
                self._wake_event.wait(wait)
                self._wake_event.clear()
            else:
                time.sleep(wait)

            if self._stop:
                break

        self.running = False

    def _needs_key_ticks(self) -> bool:
        # Check once per second whether any key has animated content
        if self.media_ticks % self.FPS != 0:
            return getattr(self, '_cached_needs_ticks', False)
        needs = False
        for key in self.deck_controller.inputs.get(Input.Key, []):
            state = key.get_active_state()
            if state.key_video is not None:
                needs = True
                break
        self._cached_needs_ticks = needs
        return needs

    def append_fps(self, fps: float) -> None:
        self.fps.append(fps)
        if len(self.fps) > self.FPS *2:
            self.fps.pop(0)

    def get_median_fps(self) -> float:
        return statistics.median(self.fps)
    
    def update_low_fps_warning(self):
        if not self.show_fps_warnings:
            return
        
        show_warning = self.get_median_fps() < self.FPS * 0.8
        if self.old_warning_state == show_warning:
            return
        self.old_warning_state = show_warning

        self.set_banner_revealed(show_warning)


    def set_show_fps_warnings(self, state: bool) -> None:
        self.show_fps_warnings = state
        if state:
            self.old_warning_state = False
        else:
            self.set_banner_revealed(False)

    def set_banner_revealed(self, state: bool) -> None:
        deck_stack_child: "DeckStackChild" = self.deck_controller.get_own_deck_stack_child()
        if deck_stack_child is None:
            return
        
        # deck_stack_child.low_fps_banner.set_revealed(show_warning)
        GLib.idle_add(deck_stack_child.low_fps_banner.set_revealed, state)


    def stop(self) -> None:
        self._stop = True
        while self.running:
            time.sleep(0.1)

    def add_task(self, method: callable, *args, **kwargs):
        self.tasks.append(MediaPlayerTask(
            deck_controller=self.deck_controller,
            page=self.deck_controller.active_page,
            _callable=method,
            args=args,
            kwargs=kwargs
        ))
        self._wake_event.set()

    def add_touchscreen_task(self, native_image: bytes):
        self.touchscreen_task = MediaPlayerSetTouchscreenImageTask(
            deck_controller=self.deck_controller,
            page=self.deck_controller.active_page,
            native_image=native_image
        )
        self._wake_event.set()

    def add_image_task(self, key_index: int, native_image: bytes):
        self.image_tasks[key_index] = MediaPlayerSetImageTask(
            deck_controller=self.deck_controller,
            page=self.deck_controller.active_page,
            key_index=key_index,
            native_image=native_image
        )
        self._wake_event.set()

    def perform_media_player_tasks(self):
        for task in self.tasks.copy():
            if task.page is self.deck_controller.active_page:
                task.run()

            try:
                self.tasks.remove(task)
            except ValueError:
                pass

        for key in list(self.image_tasks.keys()):
            try:
                self.image_tasks[key].run()
                del self.image_tasks[key]
            except KeyError:
                pass

        if self.touchscreen_task is not None:
            self.touchscreen_task.run()
            del self.touchscreen_task
            self.touchscreen_task = None
    def check_connection(self):
        try:
            self.deck_controller.deck.get_firmware_version()
        except StreamDeck.TransportError as e:
            log.error(f"Seams like the deck is not connected. Error: {e}")
            MediaPlayerSetImageTask.n_failed_in_row[self.deck_controller.serial_number()] += 1
            if MediaPlayerSetImageTask.n_failed_in_row[self.deck_controller.serial_number()] > 5:
                log.debug(f"Failed to contact the deck 5 times in a row: {self.deck_controller.serial_number()}. Removing controller")
                
                self.deck_controller.deck.close()
                self.deck_controller.media_player.running = False # Set stop flat - otherwise remove_controller will wait until this task is done, which it never will because it waiuts
                gl.deck_manager.remove_controller(self.deck_controller)

                gl.deck_manager.connect_new_decks()
