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
# Import Python modules
from concurrent.futures import ThreadPoolExecutor
from copy import copy
from functools import lru_cache
import os
from queue import Queue
import random
import statistics
from threading import Thread, Timer
import threading
import time
from PIL import Image, ImageOps, ImageDraw, ImageFont, ImageSequence
from StreamDeck.DeviceManager import DeviceManager
from StreamDeck.ImageHelpers import PILHelper
from StreamDeck.Devices import StreamDeck
import usb.core
import usb.util
from loguru import logger as log
import asyncio
import matplotlib.font_manager
from src.backend.DeckManagement.Subclasses.SingleKeyAsset import SingleKeyAsset
from src.backend.DeckManagement.Subclasses.background_video_cache import BackgroundVideoCache
from src.backend.DeckManagement.Subclasses.key_video_cache import VideoFrameCache
from dataclasses import dataclass
import gc

# Import own modules
from src.backend.DeckManagement.HelperMethods import *
from src.backend.DeckManagement.ImageHelpers import *
from src.backend.PageManagement.Page import Page, NoActionHolderFound
from src.backend.DeckManagement.Subclasses.ScreenSaver import ScreenSaver

import psutil
process = psutil.Process()

# Import signals
from src.Signals import Signals

# Import typing
from typing import TYPE_CHECKING, ClassVar

from src.windows.mainWindow.elements.KeyGrid import KeyButton, KeyGrid
if TYPE_CHECKING:
    from src.windows.mainWindow.elements.DeckStackChild import DeckStackChild
    from src.backend.DeckManagement.DeckManager import DeckManager
    from src.backend.PluginManager.ActionBase import ActionBase

# Import globals
import globals as gl

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
            MediaPlayerSetImageTask.n_failed_in_row[self.deck_controller.serial_number()] += 1
            if MediaPlayerSetImageTask.n_failed_in_row[self.deck_controller.serial_number()] > 5:
                log.debug(f"Failed to set key_image for 5 times in a row for deck {self.deck_controller.serial_number()}. Removing controller")
                gl.deck_manager.remove_controller(self.deck_controller)


class MediaPlayerThread(threading.Thread):
    def __init__(self, deck_controller: "DeckController"):
        super().__init__(name="MediaPlayerThread", daemon=True)
        self.deck_controller: DeckController = deck_controller
        self.FPS = 30 # Max refresh rate of the internal displays

        self.running = False
        self.media_ticks = 0

        self.pause = False
        self._stop = False

        self.task_queue: Queue[MediaPlayerTask] = Queue()
        # self.tasks = {}
        self.image_tasks = {}

        self.fps: list[float] = []
        self.old_warning_state = False

        self.show_fps_warnings = gl.settings_manager.get_app_settings().get("warnings", {}).get("enable-fps-warnings", True)

    def run(self):
        self.running = True
        while True:
            start = time.time()
            if not self.pause:
                if self.deck_controller.background.video is not None:
                    if self.deck_controller.background.video.page is self.deck_controller.active_page:
                        # There is a background video
                        video_each_nth_frame = self.FPS // self.deck_controller.background.video.fps
                        if self.media_ticks % video_each_nth_frame == 0:
                            self.deck_controller.background.update_tiles()

                for key in self.deck_controller.keys:
                    # break
                    if key.key_video is not None:
                        video_each_nth_frame = self.FPS // key.key_video.fps
                        if self.media_ticks % video_each_nth_frame == 0:
                            key.update()
                    elif self.deck_controller.background.video is not None:
                        key.update()

                # self.deck_controller.update_all_keys()

                # Perform media player tasks
                self.perform_media_player_tasks()

            self.media_ticks += 1

            # Wait for approximately 1/30th of a second before the next call
            end = time.time()
            # print(f"possible FPS: {1 / (end - start)}")
            self.append_fps(1 / (end - start))
            self.update_low_fps_warning()
            wait = max(0, 1/self.FPS - (end - start))
            time.sleep(wait)

            if self._stop:
                break

        self.running = False

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
        self.tasks.put(MediaPlayerTask(
            deck_controller=self.deck_controller,
            page=self.deck_controller.active_page,
            _callable=method,
            args=args,
            kwargs=kwargs
        ))

    def add_image_task(self, key_index: int, native_image: bytes):
        self.image_tasks[key_index] = MediaPlayerSetImageTask(
            deck_controller=self.deck_controller,
            page=self.deck_controller.active_page,
            key_index=key_index,
            native_image=native_image
        )

    def perform_media_player_tasks(self):
        while not self.task_queue.empty():
            task = self.task_queue.get()
            # Skip task if it is from another page
            if task.page is not self.deck_controller.active_page:
                continue
            task.run()

        for key in list(self.image_tasks.keys()):
            try:
                self.image_tasks[key].run()
                del self.image_tasks[key]
            except KeyError:
                pass

class DeckController:
    def __init__(self, deck_manager: "DeckManager", deck: StreamDeck.StreamDeck):
        self.deck_manager: DeckManager = deck_manager
        self.deck: StreamDeck = deck
        # Open the deck
        deck.open()
        
        try:
            # Clear the deck
            self.clear()
        except Exception as e:
            log.error(f"Failed to clear deck, maybe it's already connected to another instance? Skipping... Error: {e}")
            del self
            return
        
        self.own_deck_stack_child: "DeckStackChild" = None
        self.own_key_grid: "KeyGridChild" = None

        self.screen_saver = ScreenSaver(deck_controller=self)

        self.spacing = (36, 36)

        # Tasks
        self.media_player_tasks: list[MediaPlayerTask] = []
        self.media_player_tasks: Queue[MediaPlayerTask] = Queue()

        self.ui_grid_buttons_changes_while_hidden: dict = {}

        self.active_page: Page = None

        self.brightness:int = 75
        #TODO: Load brightness from settings
        self.set_brightness(self.brightness)

        self.keys: list[ControllerKey] = []
        self.init_keys()

        self.background = Background(self)

        self.deck.set_key_callback(self.key_change_callback)

        # Start media player thread
        self.media_player = MediaPlayerThread(deck_controller=self)
        self.media_player.start()

        self.keep_actions_ticking = True
        self.TICK_DELAY = 1
        self.tick_thread = Thread(target=self.tick_actions, name="tick_actions")
        self.tick_thread.start()

        self.page_auto_loaded: bool = False
        self.last_manual_loaded_page_path: str = None

        self.load_default_page()

    def init_keys(self):
        self.keys: list[ControllerKey] = []
        for i in range(self.deck.key_count()):
            self.keys.append(ControllerKey(self, i))

    @lru_cache(maxsize=None)
    def serial_number(self) -> str:
        return self.deck.get_serial_number()
    

    def update_key(self, index: int):
        image = self.keys[index].get_current_deck_image()
        native_image = PILHelper.to_native_key_format(self.deck, image.convert("RGB"))

        self.media_player.add_image_task(index, native_image)

        self.keys[index].set_ui_key_image(image)

    def update_all_keys(self):
        start = time.time()
        if not self.get_alive(): return
        if self.background.video is not None:
            log.debug("Skipping update_all_keys because there is a background video")
            return
        for i in range(self.deck.key_count()):
            self.update_key(i)

        log.debug(f"Updating all keys took {time.time() - start} seconds")
    

    def set_deck_key_image(self, key: int, image) -> None:
        if not self.get_alive(): return
        try:
            with self.deck:
                self.deck.set_key_image(key, image)
        except StreamDeck.TransportError as e:
            log.error(f"Failed to set deck key image. Error: {e}")

    def key_change_callback(self, deck, key, state):
        screensaver_was_showing = self.screen_saver.showing
        if state:
            # Only on key down this allows plugins to control screen saver without directly deactivating it
            self.screen_saver.on_key_change()
        
        if screensaver_was_showing:
            return

        self.keys[key].on_key_change(state)

    ### Helper methods
    def generate_alpha_key(self) -> Image.Image:
        return Image.new("RGBA", self.get_key_image_size(), (0, 0, 0, 0))
    
    def get_key_image_size(self) -> tuple[int]:
        if not self.get_alive(): return
        return self.deck.key_image_format()["size"]
    
    # ------------ #
    # Page Loading #
    # ------------ #

    def load_default_page(self):
        if not self.get_alive(): return
        default_page_path = gl.page_manager.get_default_page_for_deck(self.deck.get_serial_number())
        if default_page_path is None:
            # Use the first page
            pages = gl.page_manager.get_pages()
            if len(pages) == 0:
                return
            default_page_path = gl.page_manager.get_pages()[0]

        if default_page_path is None:
            return
        
        page = gl.page_manager.get_page(default_page_path, self)
        self.load_page(page)

    def load_background(self, page: Page, update: bool = True):
        log.info(f"Loading background in thread: {threading.get_ident()}")
        deck_settings = self.get_deck_settings()
        def set_from_deck_settings(self: "DeckController"):
            if deck_settings.get("background", {}).get("enable", False):
                loop = deck_settings.get("background", {}).get("loop", True)
                fps = deck_settings.get("background", {}).get("fps", 30)
                self.background.set_from_path(deck_settings.get("background", {}).get("path"), update=update, loop=loop, fps=fps)
            else:
                self.background.set_from_path(None, update=update)

        def set_from_page(self: "DeckController"):
            if not page.dict.get("background", {}).get("show", True):
                self.background.set_from_path(None, update=update)
            else:
                loop = page.dict.get("background", {}).get("loop", True)
                fps = page.dict.get("background", {}).get("fps", 30)
                self.background.set_from_path(page.dict.get("background", {}).get("path"), update=update, loop=loop, fps=fps)

        if page.dict.get("background", {}).get("overwrite", False) is False and "background" in deck_settings:
            set_from_deck_settings(self)
        else:
            set_from_page(self)

    def load_brightness(self, page: Page):
        if not self.get_alive(): return
        deck_settings = self.get_deck_settings()
        def set_from_deck_settings(self: "DeckController"):
            self.set_brightness(deck_settings.get("brightness", {}).get("value", 75))

        def set_from_page(self: "DeckController"):
            self.set_brightness(page.dict.get("brightness", {}).get("value", 75))

        if "brightness" in deck_settings:
            set_from_deck_settings(self)
        else:
            set_from_page(self)

    def load_screensaver(self, page: Page):
        deck_settings = self.get_deck_settings()
        def set_from_deck_settings(self: "DeckController"):
            path = deck_settings.get("screensaver", {}).get("path")
            enable = deck_settings.get("screensaver", {}).get("enable", False)
            loop = deck_settings.get("screensaver", {}).get("loop", False)
            fps = deck_settings.get("screensaver", {}).get("fps", 30)
            time = deck_settings.get("screensaver", {}).get("time-delay", 5)
            brightness = deck_settings.get("screensaver", {}).get("brightness", 30)

            self.screen_saver.set_media_path(path)
            self.screen_saver.set_enable(enable)
            self.screen_saver.set_time(time)
            self.screen_saver.set_loop(loop)
            self.screen_saver.set_fps(fps)
            self.screen_saver.set_brightness(brightness)

        def set_from_page(self: "DeckController"):
            path = page.dict.get("screensaver", {}).get("path")
            enable = page.dict.get("screensaver", {}).get("enable", False)
            loop = page.dict.get("screensaver", {}).get("loop", False)
            fps = page.dict.get("screensaver", {}).get("fps", 30)
            time = page.dict.get("screensaver", {}).get("time-delay", 5)
            brightness = page.dict.get("screensaver", {}).get("brightness", 30)

            self.screen_saver.set_media_path(path)
            self.screen_saver.set_enable(enable)
            self.screen_saver.set_time(time)
            self.screen_saver.set_loop(loop)
            self.screen_saver.set_fps(fps)
            self.screen_saver.set_brightness(brightness)

        if self.active_page.dict.get("screensaver", {}).get("overwrite", False) is False and "screensaver" in deck_settings:
            set_from_deck_settings(self)
        else:
            set_from_page(self)

    def load_all_keys(self, page: Page, update: bool = True):
        start = time.time()
        keys_to_load = self.keys
        with ThreadPoolExecutor() as executor:
            futures = [executor.submit(self.load_key, key.key, page, update) for key in keys_to_load]
            for future in futures:
                future.result()
        log.info(f"Loading all keys took {time.time() - start} seconds")

    def load_key(self, key: int, page: Page, update: bool = True, load_labels: bool = True, load_media: bool = True):
        if key >= self.deck.key_count():
            return
        coords = self.index_to_coords(key)
        key_dict = page.dict.get("keys", {}).get(f"{coords[0]}x{coords[1]}", {})
        self.keys[key].load_from_page_dict(key_dict, update, load_labels, load_media)

    def update_ui_on_page_change(self):
        # Update ui
        if recursive_hasattr(gl, "app.main_win.sidebar"):
            try:
                # gl.app.main_win.header_bar.page_selector.update_selected()
                settings_page = gl.app.main_win.leftArea.deck_stack.get_visible_child().page_settings.settings_page
                settings_group = settings_page.settings_group
                background_group = settings_page.background_group

                # Update ui
                settings_group.brightness.load_defaults_from_page()
                settings_group.screensaver.load_defaults_from_page()
                background_group.media_row.load_defaults_from_page()

                gl.app.main_win.sidebar.reload()
            except AttributeError as e:
                log.error(f"{e} -> This is okay if you just activated your first deck.")

    def close_image_ressources(self):
        for key in self.keys:
            key.close_resources()

        if self.background.video is not None:
            self.background.video.close()
        if self.background.image is not None:
            self.background.image.close()


    def load_page(self, page: Page, load_brightness: bool = True, load_screensaver: bool = True, load_background: bool = True, load_keys: bool = True,
                  allow_reload: bool = True):
        if not self.get_alive(): return

        start = time.time()

        if not allow_reload:
            if self.active_page is page:
                return
        
        old_path = self.active_page.json_path if self.active_page is not None else None

        if self.active_page is not None and False:
            self.active_page.clear_action_objects()
        # self.active_page = None

        self.active_page = page

        if page is None:
            # Clear deck
            self.clear()
            return

        log.info(f"Loading page {page.get_name()} on deck {self.deck.get_serial_number()}")

        # Stop queued tasks
        self.clear_media_player_tasks()

        # Update ui
        GLib.idle_add(self.update_ui_on_page_change) #TODO: Use new signal manager instead

        if load_background:
            # self.load_background(page, update=False)
            self.media_player.add_task(self.load_background, page, update=False)
        if load_brightness:
            self.load_brightness(page)
        if load_screensaver:
            self.load_screensaver(page)
        if load_keys:
            self.media_player.add_task(self.load_all_keys, page, update=False)

        # Load page onto deck
        # self.update_all_keys()
        self.media_player.add_task(self.update_all_keys)

        # Notify plugin actions
        gl.signal_manager.trigger_signal(Signals.ChangePage, self, old_path, self.active_page.json_path)

        log.info(f"Loading page {page.get_name()} on deck {self.deck.get_serial_number()} took {time.time() - start} seconds")

    def set_brightness(self, value):
        if not self.get_alive(): return
        self.deck.set_brightness(int(value))
        self.brightness = value

    def tick_actions(self) -> None:
        while self.keep_actions_ticking:
            time.sleep(self.TICK_DELAY)
            if not self.screen_saver.showing and True:
                for key in self.keys:
                    key.own_actions_tick()
            else:
                for key in self.keys:
                    key.update()
            
        

    # -------------- #
    # Helper methods #
    # -------------- #
        
    def index_to_coords(self, index):
        if not self.get_alive(): return
        rows, cols = self.deck.key_layout()    
        y = index // cols
        x = index % cols
        return x, y
    
    def coords_to_index(self, coords):
        if not self.get_alive(): return
        x, y = map(int, coords)
        rows, cols = self.deck.key_layout()
        return y * cols + x
    
    def get_deck_settings(self):
        if not self.get_alive(): return {}
        return gl.settings_manager.get_deck_settings(self.deck.get_serial_number())
    
    def get_own_deck_stack_child(self) -> "DeckStackChild":
        # Why not just lru_cache this? Because this would also cache the None that gets returned while the ui is still loading
        if self.own_deck_stack_child is not None:
            return self.own_deck_stack_child
        
        if not recursive_hasattr(gl, "app.main_win.leftArea.deck_stack"): return
        serial_number = self.deck.get_serial_number()
        deck_stack = gl.app.main_win.leftArea.deck_stack
        deck_stack_child = deck_stack.get_child_by_name(serial_number)
        if deck_stack_child == None:
            return
        
        self.own_deck_stack_child = deck_stack_child
        return deck_stack_child
    
    def clear(self):
        alpha_image = self.generate_alpha_key()
        native_image = PILHelper.to_native_key_format(self.deck, alpha_image.convert("RGB"))
        for i in range(self.deck.key_count()):
            self.deck.set_key_image(i, native_image)

    def get_own_key_grid(self) -> KeyGrid:
        # Why not just lru_cache this? Because this would also cache the None that gets returned while the ui is still loading
        if self.own_key_grid is not None:
            return self.own_key_grid
        
        deck_stack_child = self.get_own_deck_stack_child()
        if deck_stack_child == None:
            return
        
        self.own_key_grid = deck_stack_child.page_settings.grid_page
        return deck_stack_child.page_settings.grid_page
    
    def clear_media_player_tasks(self):
        while not self.media_player.task_queue.empty():
            self.media_player.task_queue.get()
        
        self.media_player.image_tasks.clear()

    def clear_media_player_tasks_via_task(self):
        self.media_player_tasks.append(MediaPlayerTask(
            deck_controller=self,
            page=self.active_page,
            _callable=self.clear_media_player_tasks,
            args=(),
            kwargs={},
        ))

    def delete(self):
        if self.active_page is not None:
            self.active_page.action_objects = {}

        self.media_player.stop()

        self.keep_actions_ticking = False
        self.deck.run_read_thread = False

    def get_alive(self) -> bool:
        try:
            return self.deck.is_open
        except Exception as e:
            log.debug(f"Cougth dead deck error. Error: {e}")
            return False


class Background:
    def __init__(self, deck_controller: DeckController):
        self.deck_controller = deck_controller

        self.image = None
        self.video = None

        self.tiles: list[Image.Image] = [None] * deck_controller.deck.key_count()

    def set_image(self, image: "BackgroundImage", update: bool = True) -> None:
        self.image = image
        if self.video is not None:
            self.video.close()
        self.video = None
        gc.collect()

        self.update_tiles()
        if update:
            self.deck_controller.update_all_keys()

    def set_video(self, video: "BackgroundVideo", update: bool = True) -> None:
        if self.video is not None:
            self.video.close()
        self.image = None
        self.video = video
        gc.collect()

        self.update_tiles()
        if update:
            self.deck_controller.update_all_keys()

    def set_from_path(self, path: str, fps: int = 30, loop: bool = True, update: bool = True, allow_keep: bool = True) -> None:
        if path == "":
            path = None
        if path is None:
            self.image = None
            # self.video = None
            self.set_video(None, update=False)
            self.update_tiles()
            if update:
                self.deck_controller.update_all_keys()
        elif is_video(path):
            if allow_keep:
                if self.video is not None and self.video.video_path == path:
                    self.video.page = self.deck_controller.active_page
                    self.video.fps = fps
                    self.video.loop = loop
                    return
            self.set_video(BackgroundVideo(self.deck_controller, path, loop=loop, fps=fps), update=update)
        else:
            if path is None:
                return
            if not os.path.isfile(path):
                return
            with Image.open(path) as image:
                self.set_image(BackgroundImage(self.deck_controller, image.copy()), update=update)

    def update_tiles(self) -> None:
        old_tiles = self.tiles # Why store them and close them later? So that there is not key error if the media threads fetches them during the update
        if self.image is not None:
            self.tiles = self.image.get_tiles()
        elif self.video is not None:
            self.tiles = self.video.get_next_tiles()
        else:
            self.tiles = [self.deck_controller.generate_alpha_key() for _ in range(self.deck_controller.deck.key_count())]

        for tile in old_tiles:
            if tile is not None:
                tile.close()
                tile = None
                del tile
        del old_tiles
        

class BackgroundImage:
    def __init__(self, deck_controller: DeckController, image: Image) -> None:
        self.deck_controller = deck_controller
        self.image = image

    def create_full_deck_sized_image(self) -> Image:
        key_rows, key_cols = self.deck_controller.deck.key_layout()
        key_width, key_height = self.deck_controller.get_key_image_size()
        spacing_x, spacing_y = 36, 36

        key_width *= key_cols
        key_height *= key_rows

        # Compute the total number of extra non-visible pixels that are obscured by
        # the bezel of the StreamDeck.
        spacing_x *= key_cols - 1
        spacing_y *= key_rows - 1

        # Compute final full deck image size, based on the number of buttons and
        # obscured pixels.
        full_deck_image_size = (key_width + spacing_x, key_height + spacing_y)

        # Resize the image to suit the StreamDeck's full image size. We use the
        # helper function in Pillow's ImageOps module so that the image's aspect
        # ratio is preserved.
        return ImageOps.fit(self.image, full_deck_image_size, Image.LANCZOS)
    
    def crop_key_image_from_deck_sized_image(self, image: Image.Image, key):
        key_spacing = (36, 36)
        deck = self.deck_controller.deck


        key_rows, key_cols = deck.key_layout()
        key_width, key_height = deck.key_image_format()['size']
        spacing_x, spacing_y = key_spacing

        # Determine which row and column the requested key is located on.
        row = key // key_cols
        col = key % key_cols

        # Compute the starting X and Y offsets into the full size image that the
        # requested key should display.
        start_x = col * (key_width + spacing_x)
        start_y = row * (key_height + spacing_y)

        # Compute the region of the larger deck image that is occupied by the given
        # key, and crop out that segment of the full image.
        region = (start_x, start_y, start_x + key_width, start_y + key_height)
        segment = image.crop(region)

        # Create a new key-sized image, and paste in the cropped section of the
        # larger image.
        key_image = PILHelper.create_key_image(deck)
        key_image.paste(segment)

        return key_image
    
    def get_tiles(self) -> list[Image.Image]:
        full_deck_sized_image = self.create_full_deck_sized_image()

        tiles: list[Image.Image] = []
        for key in range(self.deck_controller.deck.key_count()):
            key_image = self.crop_key_image_from_deck_sized_image(full_deck_sized_image, key)
            tiles.append(key_image)

        return tiles


class BackgroundVideo(BackgroundVideoCache):
    def __init__(self, deck_controller: DeckController, video_path: str, loop: bool = True, fps: int = 30) -> None:
        self.deck_controller = deck_controller
        self.video_path = video_path
        self.loop = loop
        self.fps = fps

        self.page: Page = self.deck_controller.active_page

        self.active_frame: int = -1

        super().__init__(video_path, deck_controller=deck_controller)

    def get_next_tiles(self) -> list[Image.Image]:
        # return [self.deck_controller.generate_alpha_key() for _ in range(self.deck_controller.deck.key_count())]
        self.active_frame += 1

        if self.active_frame >= self.n_frames:
            if self.loop:
                self.active_frame = 0

        tiles =  self.get_tiles(self.active_frame)
        try:
            copied_tiles = [tile.copy() for tile in tiles]
        except:
            copied_tiles = [None for _ in range(len(tiles))]
        return copied_tiles

        frame = self.get_next_frame()
        frame_full_sized_image = self.create_full_deck_sized_image(frame)

        tiles: list[Image.Image] = []
        for key in range(self.deck_controller.deck.key_count()):
            key_image = self.crop_key_image_from_deck_sized_image(frame_full_sized_image, key)
            tiles.append(key_image)

        return tiles

    def get_next_frame(self) -> Image.Image:
        self.active_frame += 1

        if self.active_frame >= self.n_frames:
            self.active_frame = 0
        
        return self.get_frame(self.active_frame)
    
    def create_full_deck_sized_image(self, frame: Image.Image) -> Image.Image:
        key_rows, key_cols = self.deck_controller.deck.key_layout()
        key_width, key_height = self.deck_controller.get_key_image_size()
        spacing_x, spacing_y = 36, 36

        key_width *= key_cols
        key_height *= key_rows

        # Compute the total number of extra non-visible pixels that are obscured by
        # the bezel of the StreamDeck.
        spacing_x *= key_cols - 1
        spacing_y *= key_rows - 1

        # Compute final full deck image size, based on the number of buttons and
        # obscured pixels.
        full_deck_image_size = (key_width + spacing_x, key_height + spacing_y)

        # Resize the image to suit the StreamDeck's full image size. We use the
        # helper function in Pillow's ImageOps module so that the image's aspect
        # ratio is preserved.
        return ImageOps.fit(frame, full_deck_image_size, Image.Resampling.HAMMING)
    
    def crop_key_image_from_deck_sized_image(self, image: Image.Image, key):
        key_spacing = (36, 36)
        deck = self.deck_controller.deck


        key_rows, key_cols = deck.key_layout()
        key_width, key_height = deck.key_image_format()['size']
        spacing_x, spacing_y = key_spacing

        # Determine which row and column the requested key is located on.
        row = key // key_cols
        col = key % key_cols

        # Compute the starting X and Y offsets into the full size image that the
        # requested key should display.
        start_x = col * (key_width + spacing_x)
        start_y = row * (key_height + spacing_y)

        # Compute the region of the larger deck image that is occupied by the given
        # key, and crop out that segment of the full image.
        region = (start_x, start_y, start_x + key_width, start_y + key_height)
        segment = image.crop(region)

        # Create a new key-sized image, and paste in the cropped section of the
        # larger image.
        key_image = PILHelper.create_key_image(deck)
        key_image.paste(segment)

        return key_image
    

class KeyGIF(SingleKeyAsset):
    def __init__(self, controller_key: "ControllerKey", gif_path: str, fill_mode: str = "cover", size: float = 1,
                 valign: float = 0, halign: float = 0, fps: int = 30, loop: bool = True):
        super().__init__(controller_key, fill_mode, size, valign, halign)
        self.gif_path = gif_path
        self.fps = fps
        self.loop = loop

        self.active_frame: int = -1

        self.gif = Image.open(self.gif_path)
        self.gif = ImageSequence.Iterator(self.gif)
        self.frames = [frame.convert("RGBA") for frame in self.gif]

    def get_next_frame(self) -> Image.Image:
        self.active_frame += 1

        if self.active_frame >= len(self.frames):
            if self.loop:
                self.active_frame = 0
            else:
                self.active_frame = len(self.frames) - 1

        return self.frames[self.active_frame]
        self.gif.convert("RGBA")
    
    def get_raw_image(self) -> Image.Image:
        return self.get_next_frame()
    
    def close(self) -> None:
        self.gif = None
        self.frames = None
        del self.gif
        del self.frames
    

class ControllerKey:
    def __init__(self, deck_controller: DeckController, key: int):
        self.deck_controller = deck_controller
        self.key = key

        self.valign = 0
        self.halign = 0
        self.fill_mode = "cover"
        self.size = 0.1

        self.background_color = [0, 0, 0, 0]

        # Keep track of the current state of the key because self.deck_controller.deck.key_states seams to give inverted values in get_current_deck_image
        self.press_state: bool = self.deck_controller.deck.key_states()[self.key]

        self.labels: dict = {}

        self.key_image: KeyImage = None
        self.key_video: KeyVideo = None
        # self.key_asset: SingleKeyAsset = SingleKeyAsset(self)

        self.hide_error_timer: Timer = None

        # self.pressed_on_page: Page = None #TODO: Block release on different page than press

    def get_current_deck_image(self) -> Image.Image:
        background: Image.Image = None
        # Only load the background image if it's not gonna be hidden by the background color
        if self.background_color[-1] < 255:
            background = copy(self.deck_controller.background.tiles[self.key])

        if self.background_color[-1] > 0:
            background_color_img = Image.new("RGBA", self.deck_controller.get_key_image_size(), color=tuple(self.background_color))
            
            if background is None:
                # Use the color as the only background - happens if background color alpha is 255
                background = background_color_img
            else:
                background.paste(background_color_img, (0, 0), background_color_img)


        if background is None:
            background = self.deck_controller.generate_alpha_key().copy()

        image: Image.Image = None
        if self.key_image is not None:
            image = self.key_image.generate_final_image(background=background, labels=self.labels)
        elif self.key_video is not None:
            image = self.key_video.generate_final_image(background=background, labels=self.labels)
        else:
            image = background
        labeled_image = self.add_labels_to_image(image)

        if self.is_pressed():
            labeled_image = self.shrink_image(labeled_image)

        if background is not None:
            background.close()
        
        image.close()

        return labeled_image
    
    def paste_foreground(self, background: Image.Image, foreground: Image.Image) -> Image.Image:
        img_size = self.deck_controller.get_key_image_size()
        img_size = (int(img_size[0] * self.size), int(img_size[1] * self.size)) # Calculate scaled size of the image
        if self.fill_mode == "stretch":
            foreground_resized = foreground.resize(img_size, Image.Resampling.HAMMING)

        elif self.fill_mode == "cover":
            foreground_resized = ImageOps.cover(foreground, img_size, Image.Resampling.HAMMING)

        elif self.fill_mode == "contain":
            foreground_resized = ImageOps.contain(foreground, img_size, Image.Resampling.HAMMING)

        left_margin = int((background.width - img_size[0]) * (self.halign + 1) / 2)
        top_margin = int((background.height - img_size[1]) * (self.valign + 1) / 2)

        if foreground.mode == "RGBA":
            background.paste(foreground_resized, (left_margin, top_margin), foreground_resized)
        else:
            background.paste(foreground_resized, (left_margin, top_margin))
        return background
    
    def update(self) -> None:
        self.deck_controller.update_key(self.key)

    def set_key_image(self, key_image: "KeyImage", update: bool = True) -> None:
        if self.key_image is not None:
            self.key_image.close()

        self.key_image = key_image
        self.key_video = None

        if update:
            self.update()

    def set_key_video(self, key_video: "KeyVideo") -> None:
        self.key_video = key_video
        if self.key_image is not None:
            self.key_image.close()
        self.key_image = None

    def add_label(self, key_label: "KeyLabel", position: str = "center", update: bool = True) -> None:
        if position not in ["top", "center", "bottom"]:
            log.error(f"Invalid position: {position}, must be one of 'top', 'center', or 'bottom'.")
            return
        
        self.labels[position] = key_label

        if update:
            self.update()

    def remove_label(self, position: str = "center", update: bool = True) -> None:
        if position not in ["top", "center", "bottom"]:
            log.error(f"Invalid position: {position}, must be one of 'top', 'center', or 'bottom'.")
            return
        
        if position not in self.labels:
            return
        del self.labels[position]

        if update:
            self.update()

    def add_labels_to_image(self, _image: Image.Image) -> Image.Image:
        # image = _image.copy()
        # _image.close()
        image = _image
        # image = Image.new("RGBA", _image.size, (0, 0, 0, 0))

        # image = Image.frombytes("RGBA", _image.size, _image.tobytes())

        draw = ImageDraw.Draw(image)
        draw.fontmode = "1" # Anti-aliased - this prevents frayed/noisy labels on the deck

        # labels = copy(self.labels) # Prevent crash if labels change during iteration
        labels = self.labels

        for label in dict(labels):
            text = labels[label].text
            if text in [None, ""]:
                continue
            # text = "text"
            font_path = labels[label].get_font_path()
            color = tuple(labels[label].color)
            font_size = labels[label].font_size
            font = ImageFont.truetype(font_path, font_size)

            if text is None:
                continue
            
            if label == "top":
                position = (image.width / 2, font_size*1.125)

            if label == "center":
                position = (image.width / 2, (image.height + font_size) / 2 - 3)

            if label == "bottom":
                position = (image.width / 2, image.height*0.875)


            start_mem = process.memory_info().rss
            draw.text(position,
                        text=text, font=font, anchor="ms",
                        fill=color, stroke_width=2,
                        stroke_fill="black")
            end = process.memory_info().rss
      
            
        draw = None
        del draw

        return image.copy()
    
    def is_pressed(self) -> bool:
        return self.press_state
    
    def add_border(self, image: Image.Image) -> Image.Image:
        image = image.copy()
        draw = ImageDraw.Draw(image)
        draw.rounded_rectangle((-1, -1, image.width, image.height), fill=None, outline=(255, 105, 0), width=8, radius=8)

        return image
    
    def shrink_image(self, image: Image.Image, factor: float = 0.7) -> Image.Image:
        image = image.copy()
        width = int(image.width * factor)
        height = int(image.height * factor)
        image = image.resize((width, height))

        background = Image.new("RGBA", self.deck_controller.get_key_image_size(), (0, 0, 0, 0))

        background.paste(image, (int((self.deck_controller.get_key_image_size()[0] - width) / 2), int((self.deck_controller.get_key_image_size()[1] - height) / 2)))

        image.close()

        return background
    
    def show_error(self, duration: int = -1):
        """
        duration: -1 for infinite
        """
        if duration == 0:
            self.stop_error_timer()
        elif duration > 0:
            self.hide_error_timer = Timer(duration, self.hide_error, args=[self.key_image, self.key_video, self.labels])
            self.hide_error_timer.start()

        with Image.open(os.path.join("Assets", "images", "error.png")) as image:
            image = image.copy()

        new_key_image = KeyImage(
            controller_key=self,
            image=image,
            size=0.7
        )

        # Reset labels
        self.labels = {}

        self.set_key_image(new_key_image)

    def hide_error(self, original_key_image: "KeyImage", original_video: "KeyVideo", original_labels: dict = {}):
        self.labels = original_labels
        
        if original_video is not None:
            self.set_key_video(original_video) # This also applies the labels
        else:
            self.set_key_image(original_key_image) # This also applies the labels

    def stop_error_timer(self):
        if self.hide_error_timer is not None:
            self.hide_error_timer.cancel()
            self.hide_error_timer = None

    def load_from_page_dict(self, page_dict, update: bool = True, load_labels: bool = True, load_media: bool = True, load_background_color: bool = True):
        """
        Attention: Disabling load_media might result into disabling custom user assets
        """
        self.close_resources()
        if page_dict in [None, {}]:
            self.clear(update=update)
            return
        
        ## Load media - why here? so that it doesn't overwrite the images chosen by the actions
        if load_media:
            self.key_image = None
            self.key_video = None
        
        if load_labels:
            self.labels = {}

        start = time.time()
        self.own_actions_ready() # Why not threaded? Because this would mean that some image changing calls might get executed after the next lines which blocks custom assets
        actions = self.get_own_actions()

        start = time.time()
        ## Load labels
        if load_labels:
            for label in page_dict.get("labels", []):
                if label in self.labels:
                    # Chosen by an action
                    continue
                key_label = KeyLabel(
                    controller_key=self,
                    text=page_dict["labels"][label].get("text"),
                    font_size=page_dict["labels"][label].get("font-size"),
                    font_name=page_dict["labels"][label].get("font-family"),
                    color=page_dict["labels"][label].get("color")
                )
                self.add_label(key_label, position=label, update=False)


        start = time.time()
        ## Load media
        if load_media:
            path = page_dict.get("media", {}).get("path", None)
            if path not in ["", None]:
                if is_image(path):
                    with Image.open(path) as image:
                        self.set_key_image(KeyImage(
                            controller_key=self,
                            image=image.copy(),
                            fill_mode=page_dict.get("media", {}).get("fill-mode", "cover"),
                            size=page_dict.get("media", {}).get("size", 1),
                            valign=page_dict.get("media", {}).get("valign", 0),
                            halign=page_dict.get("media", {}).get("halign", 0),
                        ), update=False)

                elif is_video(path) and True:
                    if os.path.splitext(path)[1].lower() == ".gif":
                        self.set_key_video(KeyGIF(
                            controller_key=self,
                            gif_path=path,
                            loop=page_dict.get("media", {}).get("loop", True),
                            fps=page_dict.get("media", {}).get("fps", 30),
                            size=page_dict.get("media", {}).get("size", 1),
                            valign=page_dict.get("media", {}).get("valign", 0),
                            halign=page_dict.get("media", {}).get("halign", 0),
                        )) # GIFs always update
                    else:
                        self.set_key_video(KeyVideo(
                            controller_key=self,
                            video_path=path,
                            loop = page_dict.get("media", {}).get("loop", True),
                            fps = page_dict.get("media", {}).get("fps", 30),
                            size = page_dict.get("media", {}).get("size", 1),
                            valign = page_dict.get("media", {}).get("valign", 0),
                            halign = page_dict.get("media", {}).get("halign", 0),
                        )) # Videos always update

            elif len(self.get_own_actions()) > 1:
                with Image.open(os.path.join("Assets", "images", "multi_action.png")) as image:
                    self.set_key_image(KeyImage(
                        controller_key=self,
                        image=image.copy(),
                    ), update=False)

        start = time.time()
        if load_background_color:
            self.background_color = page_dict.get("background", {}).get("color", [0, 0, 0, 0])
            # Ensure the background color has an alpha channel
            if len(self.background_color) == 3:
                self.background_color.append(255)


        if update:
            self.update()

    def clear(self, update: bool = True):
        self.key_image = None
        self.key_video = None
        self.labels = {}
        self.background_color = [0, 0, 0, 0]
        if update:
            self.update()

    def set_ui_key_image(self, image: Image.Image) -> None:
        if image is None:
            return
        
        x, y = self.deck_controller.index_to_coords(self.key)
        
        if self.deck_controller.get_own_key_grid() is None:
            # Save to use later
            self.deck_controller.ui_grid_buttons_changes_while_hidden[(y, x)] = image # The ui key coords are in reverse order
        else:
            # self.get_own_key_grid().buttons[y][x].set_image(pixbuf)
            GLib.idle_add(self.deck_controller.get_own_key_grid().buttons[y][x].set_image, image)
        
    def get_own_ui_key(self) -> KeyButton:
        x, y = self.deck_controller.index_to_coords(self.key)
        buttons = self.deck_controller.get_own_key_grid().buttons # The ui key coords are in reverse order
        return buttons[x][y]
    
    def get_own_actions(self) -> list["ActionBase"]:
        active_page = self.deck_controller.active_page
        if active_page is None:
            return []
        if active_page.action_objects is None:
            return []
        own_coords = self.deck_controller.index_to_coords(self.key)
        page_coords = f"{own_coords[0]}x{own_coords[1]}"
        actions =  active_page.get_all_actions_for_key(page_coords)

        return actions

        actions = list(active_page.action_objects.get(page_coords, {}).values())
        # Remove all NoActionHolderFound objects
        actions = [action for action in actions if not (isinstance(action, NoActionHolderFound) or action is None)]
        return actions
    
    def on_key_change(self, state) -> None:
        self.press_state = state

        self.update()

        if state:
            self.own_actions_key_down_threaded()
        else:
            self.own_actions_key_up_threaded()

    def own_actions_ready_threaded(self) -> None:
        threading.Thread(target=self.own_actions_ready, name="own_actions_ready").start()

    def own_actions_key_down_threaded(self) -> None:
        threading.Thread(target=self.own_actions_key_down, name="own_actions_key_down").start()

    def own_actions_key_up_threaded(self) -> None:
        threading.Thread(target=self.own_actions_key_up, name="own_actions_key_up").start()

    def own_actions_tick_threaded(self) -> None:
        threading.Thread(target=self.own_actions_tick, name="own_actions_tick").start()



    def own_actions_ready(self) -> None:
        with ThreadPoolExecutor() as executor:
            futures = [executor.submit(action.on_ready) for action in self.get_own_actions()]
            for future in futures:
                future.result()

    def own_actions_key_down(self) -> None:
        for action in self.get_own_actions():
            action.on_key_down()

    def own_actions_key_up(self) -> None:
        for action in self.get_own_actions():
            action.on_key_up()

    def own_actions_tick(self) -> None:
        for action in self.get_own_actions():
            action.on_tick()

    def close_resources(self) -> None:
        if self.key_image is not None:
            self.key_image.close()
            self.key_image = None
            del self.key_image
        if self.key_video is not None:
            self.key_video.close()
            self.key_video = None
            del self.key_video

        self.labels.clear()


class KeyLabel:
    def __init__(self, controller_key: ControllerKey, text: str, font_size: int = 15, font_name: str = None, color: list[int] = [255, 255, 255, 255]):
        if text is None:
            text = ""

        self.controller_key = controller_key
        self.text = text
        self.font_size = font_size
        self.font_name = font_name
        self.color = color

    def get_font_path(self) -> str:
        if self.font_name is None and False:
            FALLBACK = os.path.join("Assets", "Fonts", "Roboto-Regular.ttf")
            return FALLBACK
        return matplotlib.font_manager.findfont(matplotlib.font_manager.FontProperties(family=self.font_name))


class KeyImage(SingleKeyAsset):
    def __init__(self, controller_key: ControllerKey, image: Image.Image, fill_mode: str = "cover", size: float = 1, valign: float = 0, halign: float = 0):
        """
        Initialize the class with the given controller key, image, fill mode, size, vertical alignment, and horizontal alignment.

        Parameters:
            controller_key (ControllerKey): The key of the controller.
            image (Image.Image): The image to be displayed.
            fill_mode (str, optional): The mode for filling the image. Defaults to "cover".
            size (float, optional): The size of the image. Defaults to 1.
            valign (float, optional): The vertical alignment of the image. Defaults to 0. Ranges from -1 to 1.
            halign (float, optional): The horizontal alignment of the image. Defaults to 0. Ranges from -1 to 1.
        """
        super().__init__(controller_key, fill_mode, size, valign, halign)
        self.image = image

        if self.image is None:
            self.image = self.controller_key.deck_controller.generate_alpha_key()

    def get_raw_image(self) -> Image.Image:
        if not hasattr(self, "image"):
            return
        return self.image
    
    def close(self) -> None:
        self.image.close()
        self.image = None
        del self.image
        return

class KeyVideo(SingleKeyAsset):
    def __init__(self, controller_key: ControllerKey, video_path: str, fill_mode: str = "cover", size: float = 1,
                 valign: float = 0, halign: float = 0, fps: int = 30, loop: bool = True):
        super().__init__(
            controller_key=controller_key,
            fill_mode=fill_mode,
            size=size,
            valign=valign,
            halign=halign
        )
        self.video_path = video_path
        self.fps = fps
        self.loop = loop

        self.video_cache = VideoFrameCache(video_path)

        self.active_frame: int = -1


    def get_next_frame(self) -> Image:
        self.active_frame += 1

        if self.active_frame >= self.video_cache.n_frames:
            if self.loop:
                self.active_frame = 0
        
        return self.video_cache.get_frame(self.active_frame).resize(self.controller_key.deck_controller.get_key_image_size(), Image.Resampling.LANCZOS)
    
    def get_raw_image(self) -> Image.Image:
        return self.get_next_frame()
     