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
import gc
import statistics
import threading
import time
# Import Python modules
from concurrent.futures import ThreadPoolExecutor
from copy import copy
from dataclasses import dataclass
from queue import Queue
from threading import Thread, Timer

import psutil
from PIL import ImageDraw, ImageFont, ImageSequence
from StreamDeck.Devices import StreamDeck
from StreamDeck.Devices.StreamDeck import DialEventType, TouchscreenEventType
from StreamDeck.Devices.StreamDeckPlus import StreamDeckPlus
from loguru import logger as log

# Import own modules
from src.backend.DeckManagement.BetterDeck import BetterDeck
from src.backend.DeckManagement.HelperMethods import *
from src.backend.DeckManagement.ImageHelpers import *
from src.backend.DeckManagement.InputIdentifier import Input, InputEvent, InputIdentifier
from src.backend.DeckManagement.Subclasses.ActionPermissionManager import ActionPermissionManager
from src.backend.DeckManagement.Subclasses.FakeDeck import FakeDeck
from src.backend.DeckManagement.Subclasses.KeyImage import InputImage
from src.backend.DeckManagement.Subclasses.KeyLabel import KeyLabel
from src.backend.DeckManagement.Subclasses.KeyLayout import ImageLayout
from src.backend.DeckManagement.Subclasses.KeyVideo import InputVideo
from src.backend.DeckManagement.Subclasses.ScreenSaver import ScreenSaver
from src.backend.DeckManagement.Subclasses.SingleKeyAsset import SingleKeyAsset
from src.backend.DeckManagement.Subclasses.background_video_cache import BackgroundVideoCache
from src.backend.PageManagement.Page import ActionOutdated, Page, NoActionHolderFound

process = psutil.Process()

from gi.repository import GLib

# Import signals
from src.Signals import Signals

# Import typing
from typing import TYPE_CHECKING, ClassVar

from src.windows.mainWindow.elements.KeyGrid import KeyButton, KeyGrid
from src.backend.PluginManager.ActionCore import ActionCore
if TYPE_CHECKING:
    from src.windows.mainWindow.elements.DeckStackChild import DeckStackChild
    from src.backend.DeckManagement.DeckManager import DeckManager

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

        self.fps: list[float] = []
        self.old_warning_state = False

        app_settings = gl.settings_manager.get_app_settings()
        self.show_fps_warnings = app_settings.get("warning", {}).get("show_fps_warnings", True)

    # @log.catch
    def run(self):
        self.running = True

        while True:
            start = time.time()

            # self.check_connection()

            if not self.pause:
                if self.deck_controller.background.video is not None:
                    if self.deck_controller.background.video.page is self.deck_controller.active_page:
                        # There is a background video
                        video_each_nth_frame = self.FPS // self.deck_controller.background.video.fps
                        if self.media_ticks % video_each_nth_frame == 0:
                            self.deck_controller.background.update_tiles()

                #TODO: generalize
                for key in self.deck_controller.inputs[Input.Key]:
                    key_state = key.get_active_state()
                    if key_state.key_video is not None:
                        video_each_nth_frame = self.FPS // key_state.key_video.fps
                        if self.media_ticks % video_each_nth_frame == 0:
                            key.update()
                    elif self.deck_controller.background.video is not None:
                        key.update()

                for dial in self.deck_controller.inputs[Input.Dial]:
                    dial_state = dial.get_active_state()
                    if dial_state.video is not None:
                        video_each_nth_frame = self.FPS // dial_state.video.fps
                        if self.media_ticks % video_each_nth_frame == 0:
                            dial.update()

                # self.deck_controller.update_all_inputs()

                # Perform media player tasks
                self.perform_media_player_tasks()

            self.media_ticks += 1

            # Wait for approximately 1/30th of a second before the next call
            end = time.time()
            # print(f"possible FPS: {1 / (end - start)}")
            self.append_fps(1 / (end - start))
            self.update_low_fps_warning()
            wait = max(0, 1 / self.FPS - (end - start))
            time.sleep(wait)

            if self._stop:
                self.running = False
                return

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

    def add_touchscreen_task(self, native_image: bytes):
        self.touchscreen_task = MediaPlayerSetTouchscreenImageTask(
            deck_controller=self.deck_controller,
            page=self.deck_controller.active_page,
            native_image=native_image
        )

    def add_image_task(self, key_index: int, native_image: bytes):
        self.image_tasks[key_index] = MediaPlayerSetImageTask(
            deck_controller=self.deck_controller,
            page=self.deck_controller.active_page,
            key_index=key_index,
            native_image=native_image
        )

    def perform_media_player_tasks(self):
        for task in self.tasks.copy():
            if task.page is self.deck_controller.active_page:
                task.run()

            try:
                self.tasks.remove(task)
            except ValueError:
                continue

        for key in list(self.image_tasks.keys()):
            try:
                self.image_tasks[key].run()
                del self.image_tasks[key]
            except KeyError:
                continue

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

class DeckController:
    def __init__(self, deck_manager: "DeckManager", deck: StreamDeck.StreamDeck):
        self.deck_manager: DeckManager = deck_manager
        # Open the deck - why store it as self.deck? So that self.get_alive() returns True in get_deck_settings
        self.deck = deck
        self.deck.open(self.deck_manager.beta_resume_mode)

        rotation = self.get_deck_settings().get("rotation", 0)
        self.deck: BetterDeck = BetterDeck(deck, rotation)

        try:
            # Clear the deck
            self.clear()
        except Exception as e:
            log.error(f"Failed to clear deck, maybe it's already connected to another instance? Skipping... Error: {e}")
            del self
            return
        
        self.hold_time: float = gl.settings_manager.get_app_settings().get("general", {}).get("hold-time", 0.5)
        
        self.own_deck_stack_child: "DeckStackChild" = None
        self.own_key_grid: "KeyGridChild" = None

        self.screen_saver = ScreenSaver(deck_controller=self)
        self.allow_interaction = True

        self.key_spacing = (36, 36)

        if isinstance(self.deck, StreamDeckPlus) or (isinstance(self.deck, FakeDeck) and self.deck.key_layout() == [2, 4]):
            self.key_spacing = (52, 36)

        # Tasks
        self.media_player_tasks: Queue[MediaPlayerTask] = Queue()

        self.ui_image_changes_while_hidden: dict = {}

        self.active_page: Page = None

        self.inputs = {}
        for i in Input.All:
            self.inputs[i] = []
        self.init_inputs()

        self.background = Background(self)

        self.deck.set_key_callback(self.key_event_callback)
        self.deck.set_dial_callback(self.dial_event_callback)
        self.deck.set_touchscreen_callback(self.touchscreen_event_callback)

        # Start media player thread
        self.media_player = MediaPlayerThread(deck_controller=self)
        self.media_player.start()

        self.keep_actions_ticking = True
        self.TICK_DELAY = gl.cli_args.tick_delay
        self.tick_thread = Thread(target=self.tick_actions, name="tick_actions")
        self.tick_thread.start()

        self.page_auto_loaded: bool = False
        self.last_manual_loaded_page_path: str = None

        deck_settings = self.get_deck_settings()

        self.brightness = 75
        brightness = deck_settings.get("brightness", {}).get("value", self.brightness)
        self.set_brightness(brightness)

        # self.rotation = 270
        # rotation = deck_settings.get("rotation", {}).get("value", self.rotation)
        # self.set_rotation(rotation)


        # If screen is locked start the screensaver - this happens when the deck gets reconnected during the screensaver
        app_settings = gl.settings_manager.get_app_settings()

        if gl.screen_locked and app_settings.get("system", {}).get("lock-on-lock-screen", True):
            self.allow_interaction = False
            self.screen_saver.show()
        else:
            self.load_default_page()

    def init_inputs(self):
        for input_obj in Input.All:
            self.inputs[input_obj] = []

            try:
                input_class = getattr(sys.modules[__name__], input_obj.controller_class_name)
            except AttributeError:
                log.error(f"Input class '{input_obj.controller_class_name}' not found. Skipping...'")
                continue

            for identifier in input_class.Available_Identifiers(self.deck):
                input_instance = input_class(self, Input.FromTypeIdentifier(input_obj.input_type, identifier))
                self.inputs[input_obj].append(input_instance)

    def get_inputs(self, identifier: InputIdentifier) -> list["ControllerInput"]:
        input_type = type(identifier)
        if input_type not in self.inputs:
            raise ValueError(f"Unknown input type: {input_type}")
        return self.inputs[input_type]

    def get_input(self, identifier: InputIdentifier) -> "ControllerInput":
        for input in self.get_inputs(identifier):
            if input.identifier == identifier:
                return input
        return None

    @lru_cache(maxsize=None)
    def serial_number(self) -> str:
        return self.deck.get_serial_number()
    
    def is_visual(self) -> bool:
        return self.deck.is_visual()

    def update_input(self, identifier: InputIdentifier):
        input = self.get_input(identifier)

        if not input:
            return

        input.update()

    @log.catch
    def update_all_inputs(self):
        if not self.get_alive():
            return

        start_time = time.time()

        if self.background.video is not None:
            log.debug(
                "Skipping full input update due to background video; updating only dials if present."
            )
            for dial_input in self.inputs.get(Input.Dial, []):
                dial_input.update()
        else:
            for input_group in self.inputs.values():
                for input_instance in input_group:
                    input_instance.update()

        elapsed = time.time() - start_time
        log.debug(f"Updating all inputs took {elapsed:.3f} seconds")

    def event_callback(self, ident: InputIdentifier, *args, **kwargs):
        if not self.allow_interaction:
            return

        input = self.get_input(ident)

        if not input:
            return

        input.event_callback(*args, **kwargs)

    def key_event_callback(self, deck, key, *args, **kwargs):
        coords = ControllerKey.Index_To_Coords(deck, key)
        if self.deck.rotation % 180 != 0:
            coords = (coords[1], coords[0])
        ident = Input.Key(f"{coords[0]}x{coords[1]}")
        self.event_callback(ident,*args, **kwargs)

    def dial_event_callback(self, deck, dial, *args, **kwargs):
        ident = Input.Dial(str(dial))
        self.event_callback(ident, *args, **kwargs)

    def touchscreen_event_callback(self, deck, *args, **kwargs):
        ident = Input.Touchscreen("sd-plus")
        self.event_callback(ident, *args, **kwargs)


    ### Helper methods
    def generate_alpha_key(self) -> Image.Image:
        return Image.new("RGBA", self.get_key_image_size(), (0, 0, 0, 0))
    
    @lru_cache(maxsize=None)
    def get_key_image_size(self) -> tuple[int, int]:
        if not self.get_alive():
            return

        size = self.deck.key_image_format()["size"]

        if size is None:
            return 72, 72

        size = max(size[0], 72), max(size[1], 72)
        return size

    @lru_cache(maxsize=None)
    def get_touchscreen_image_size(self) -> tuple[int, int]:
        if not self.get_alive():
            return

        size = self.deck.touchscreen_image_format()["size"]

        if size is None:
            return 800, 100

        size = max(size[0], 800), max(size[1], 100)
        return size

    # ------------ #
    # Page Loading #
    # ------------ #

    def load_default_page(self):
        if not self.get_alive(): return

        api_page_path = None

        # TODO: REWORK PAGE REQUESTS
        if self.serial_number() in gl.api_page_requests:
            api_page_path = gl.api_page_requests[self.serial_number()]
            api_page_path = gl.page_manager.get_best_page_path_match_from_name(api_page_path)

        if api_page_path is None:
            default_page_path = gl.page_manager.get_default_page_for_deck(self.deck.get_serial_number())
        else:
            default_page_path = api_page_path

        if default_page_path is not None:
            if not os.path.isfile(default_page_path):
                default_page_path = None

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

    @log.catch
    def load_background(self, page: Page, update: bool = True):
        log.info(f"Loading background in thread: {threading.get_ident()}")

        deck_settings = self.get_deck_settings().get("background", {})
        page_settings = page.dict.get("background", {})

        use_dict = {}

        if not page_settings.get("overwrite", False) and deck_settings.get("enable", False):
            use_dict = deck_settings
        elif page_settings.get("show", True) and page_settings.get("overwrite", False):
            use_dict = page_settings

        if use_dict:
            self.background.set_from_path(
                path=use_dict.get("path", ""),
                update=update,
                loop=use_dict.get("loop", True),
                fps=use_dict.get("fps", 30)
            )
        else:
            self.background.set_from_path(None, update=update)

    @log.catch
    def load_brightness(self, page: Page):
        if not self.get_alive():
            return

        deck_settings = self.get_deck_settings().get("brightness", {})
        page_settings = page.dict.get("brightness", {})

        if page_settings.get("overwrite", False):
            use_dict = page_settings
        else:
            use_dict = deck_settings

        self.set_brightness(use_dict.get("value", 75))

    @log.catch
    def load_screensaver(self, page: Page):
        deck_settings = self.get_deck_settings().get("screensaver", {})
        page_settings = page.dict.get("screensaver", {})

        if not self.active_page.dict.get("screensaver", {}).get("overwrite"):
            use_dict = deck_settings
        else:
            use_dict = page_settings

        self.screen_saver.set_media_path(use_dict.get("path", None))
        self.screen_saver.set_enable(use_dict.get("enable", False))
        self.screen_saver.set_loop(use_dict.get("loop", False))
        self.screen_saver.set_fps(use_dict.get("fps", 30))
        self.screen_saver.set_time(use_dict.get("time-delay", 5))
        self.screen_saver.set_brightness(use_dict.get("brightness", 30))

    @log.catch
    def load_all_inputs(self, page: Page, update: bool = True):
        start = time.time()

        with ThreadPoolExecutor() as executor:
            futures = []
            for input_group in self.inputs.values():
                for controller_input in input_group:
                    futures.append(executor.submit(self.load_input, controller_input, page, update))

            for future in futures:
                try:
                    future.result()
                except Exception as e:
                    log.error(f"Error loading input: {e}")

        log.info(f"Loading all inputs took {time.time() - start} seconds")

    def load_input_from_identifier(self, identifier: str, page: Page, update: bool = True):
        controller_input = self.get_input(identifier)
        if controller_input is not None:
            self.load_input(controller_input, page, update)

    def load_input(self, controller_input: "ControllerInput", page: Page, update: bool = True):
        input_dict = controller_input.identifier.get_config(page)
        controller_input.load_from_input_dict(input_dict, update)

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

                gl.app.main_win.sidebar.update()
            except AttributeError as e:
                log.error(f"{e} -> This is okay if you just activated your first deck.")


    def close_image_resources(self):
        for input_group in self.inputs.values():
            for input_instance in input_group:
                input_instance.close_resources()

        if self.background.video is not None:
            self.background.video.close()

        if self.background.image is not None:
            self.background.image.close()

    @log.catch
    def load_page(self, page: Page, load_brightness: bool = True, load_screensaver: bool = True, load_background: bool = True, load_inputs: bool = True, allow_reload: bool = True):
        if not self.get_alive():
            return

        if not allow_reload and self.active_page is page:
            return

        if self.active_page is not None:
            old_path = self.active_page.json_path
        else:
            old_path = None

        self.active_page = page

        if self.active_page is None:
            self.clear()
            return

        log.info(f"Loading page {page.get_name()} on deck {self.deck.get_serial_number()}")

        # Stop queued tasks
        self.clear_media_player_tasks()

        old_tick = self.media_player.media_ticks
        old_time = time.time()
        while self.media_player.media_ticks <= old_tick and time.time() - old_time <= 0.5:
            time.sleep(0.05)

        # Update ui
        GLib.idle_add(self.update_ui_on_page_change) #TODO: Use new signal manager instead

        if load_background:
            self.media_player.add_task(self.load_background, page, update=False)
        if load_brightness:
            self.load_brightness(page)
        if load_screensaver:
            self.load_screensaver(page)
        if load_inputs:
            self.media_player.add_task(self.load_all_inputs, page, update=False)

        self.active_page.call_actions_ready_and_set_flag()

        # Load page onto deck
        self.media_player.add_task(self.update_all_inputs)

        # Notify plugin actions
        gl.signal_manager.trigger_signal(Signals.ChangePage, self, old_path, self.active_page.json_path)

        log.info(f"Loaded page {page.get_name()} on deck {self.deck.get_serial_number()}")
        gc.collect()

    def set_brightness(self, value):
        value = min(100, max(0, value))
        if not self.get_alive(): return
        self.deck.set_brightness(int(value))
        self.brightness = value

    def set_rotation(self, value):
        self.deck.set_rotation(value)

        self.own_key_grid = None


        if recursive_hasattr(gl, "app.main_win"):
            # self.get_own_key_grid().regenerate_buttons()

            # Re-generate key grid
            deck_stack_child = self.get_own_deck_stack_child()
            deck_config = deck_stack_child.page_settings.deck_config
            key_grid = deck_config.grid
            deck_config.remove(key_grid)

            deck_config.grid = KeyGrid(self, key_grid.page_settings_page)
            deck_config.prepend(deck_config.grid)

        if not self.get_alive(): return
        self.load_page(self.active_page)
        # self.update_all_inputs()


    def tick_actions(self) -> None:
        time.sleep(self.TICK_DELAY)

        while self.keep_actions_ticking:
            start = time.time()

            self.mark_page_ready_to_clear(False)

            for input_group in self.inputs.values():
                for input_instance in input_group:
                    if not self.screen_saver.showing:
                        input_instance.get_active_state().own_actions_tick_threaded()
                    else:
                        input_instance.update()

            self.mark_page_ready_to_clear(True)

            end = time.time()
            wait = max(0.1, self.TICK_DELAY - (end - start))
            time.sleep(wait)

    # -------------- #
    # Helper methods #
    # -------------- #

    def coords_to_index(self, coords: tuple) -> int:
        return ControllerKey.Coords_To_Index(self.deck, coords)
    
    def index_to_coords(self, index: int) -> tuple:
        return ControllerKey.Index_To_Coords(self.deck, index)
    
    def get_key_by_coords(self, coords: tuple) -> "ControllerKey":
        index = self.coords_to_index(coords)
        return self.get_key_by_index(index)
    
    def get_key_by_index(self, index: int) -> "ControllerKey":
        keys = self.inputs.get(Input.Key, [])
        if index < 0 or index >= len(keys):
            return
        return keys[index]

    def mark_page_ready_to_clear(self, ready_to_clear: bool):
        if self.active_page is not None:
            self.active_page.ready_to_clear = ready_to_clear
    
    def get_deck_settings(self):
        if not self.get_alive():
            return {}
        return gl.settings_manager.get_deck_settings(self.deck.get_serial_number())
    
    def get_own_deck_stack_child(self) -> "DeckStackChild":
        # Why not just lru_cache this? Because this would also cache the None that gets returned while the ui is still loading
        if self.own_deck_stack_child is not None:
            return self.own_deck_stack_child
        
        if not recursive_hasattr(gl, "app.main_win.leftArea.deck_stack"):
            return

        serial_number = self.deck.get_serial_number()
        deck_stack = gl.app.main_win.leftArea.deck_stack
        deck_stack_child = deck_stack.get_child_by_name(serial_number)

        if deck_stack_child is None:
            return
        
        self.own_deck_stack_child = deck_stack_child
        return deck_stack_child
    
    def clear(self):
        if not self.is_visual():
            return

        alpha_image = self.generate_alpha_key()
        native_image = PILHelper.to_native_key_format(self.deck, alpha_image.convert("RGB"))

        for i in range(self.deck.key_count()):
            self.deck.set_key_image(i, native_image)

        if self.deck.is_touch():
            touchscreen_size = self.get_touchscreen_image_size()
            empty = Image.new("RGB", touchscreen_size, (0, 0, 0))
            native_image = PILHelper.to_native_touchscreen_format(self.deck, empty)

            self.deck.set_touchscreen_image(native_image, x_pos=0, y_pos=0, width=touchscreen_size[0], height=touchscreen_size[1])

    def get_own_key_grid(self) -> KeyGrid:
        # Why not just lru_cache this? Because this would also cache the None that gets returned while the ui is still loading
        if self.own_key_grid is not None:
            return self.own_key_grid
        
        deck_stack_child = self.get_own_deck_stack_child()

        if deck_stack_child is None:
            return
        
        self.own_key_grid = deck_stack_child.page_settings.deck_config.grid
        return deck_stack_child.page_settings.deck_config.grid
    
    def clear_media_player_tasks(self):
        ticks = self.media_player.media_ticks
        self.media_player.tasks.clear()
        self.media_player.image_tasks.clear()

        # Wait until tick is over
        while self.media_player.media_ticks <= ticks:
            time.sleep(1/60)

    def clear_media_player_tasks_via_task(self):
        self.media_player_tasks.append(MediaPlayerTask(
            deck_controller=self,
            page=self.active_page,
            _callable=self.clear_media_player_tasks,
            args=(),
            kwargs={},
        ))

    def delete(self):
        if hasattr(self, "active_page") and self.active_page is not None:
            self.active_page.action_objects = {}

        if hasattr(self, "media_player"):
            self.media_player.stop()

        self.keep_actions_ticking = False
        self.deck.run_read_thread = False

    def get_alive(self) -> bool:
        try:
            return self.deck.is_open()
        except Exception as e:
            log.debug(f"Caught dead deck error. Error: {e}")
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
            self.deck_controller.update_all_inputs()

    def set_video(self, video: "BackgroundVideo", update: bool = True) -> None:
        if self.video is not None:
            self.video.close()
        self.image = None
        self.video = video
        gc.collect()

        self.update_tiles()
        if update:
            self.deck_controller.update_all_inputs()

    def set_from_path(self, path: str, fps: int = 30, loop: bool = True, update: bool = True, allow_keep: bool = True) -> None:
        if path == "":
            path = None

        if path is None:
            self.image = None
            self.set_video(None, update=False)
            self.update_tiles()

            if update:
                self.deck_controller.update_all_inputs()
        elif is_video(path):
            if allow_keep and self.video is not None and self.video.video_path == path:
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
            if tile is None:
                continue
            tile.close()
        del old_tiles

class BackgroundImage:
    def __init__(self, deck_controller: DeckController, image: Image) -> None:
        self.deck_controller = deck_controller
        self.image = image

    def create_full_deck_sized_image(self) -> Image:
        key_rows, key_cols = self.deck_controller.deck.key_layout()
        key_width, key_height = self.deck_controller.get_key_image_size()
        spacing_x, spacing_y = self.deck_controller.key_spacing

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
        deck = self.deck_controller.deck


        key_rows, key_cols = deck.key_layout()
        key_width, key_height = deck.key_image_format()['size']
        spacing_x, spacing_y = self.deck_controller.key_spacing

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

        # TODO: MOVE IT TO THE TOP OF __init__ when the super() logic can be executed first
        super().__init__(video_path, deck_controller=deck_controller)

    def get_next_tiles(self) -> list[Image.Image]:
        # return [self.deck_controller.generate_alpha_key() for _ in range(self.deck_controller.deck.key_count())]
        self.active_frame += 1

        if self.active_frame >= self.n_frames and self.loop:
            self.active_frame = 0

        tiles = self.get_tiles(self.active_frame)
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

        if self.active_frame >= self.n_frames and self.loop:
            self.active_frame = 0
        
        return self.get_frame(self.active_frame)
    
    def create_full_deck_sized_image(self, frame: Image.Image) -> Image.Image:
        key_rows, key_cols = self.deck_controller.deck.key_layout()
        key_width, key_height = self.deck_controller.get_key_image_size()
        spacing_x, spacing_y = self.deck_controller.key_spacing

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
        key_spacing = self.deck_controller.key_spacing
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
    def __init__(self, controller_key: "ControllerKey", gif_path: str, fps: int = 30, loop: bool = True):
        super().__init__(controller_key)
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

class LabelManager:
    def __init__(self, controller_input: "ControllerInput"):
        self.controller_input = controller_input
        
        self.page_labels = {}
        self.action_labels = {}

        self.init_labels()

    def init_labels(self):
        for position in ["top", "center", "bottom"]:
            self.page_labels[position] = KeyLabel(self.controller_input)
            self.action_labels[position] = KeyLabel(self.controller_input)
 
    def clear_labels(self):
        self.init_labels()

    def set_page_label(self, position: str, label: "KeyLabel", update: bool = True):
        if label is None:
            label = self.page_labels[position]
            label.clear_values()
        else:
            self.page_labels[position] = label
        
        if update:
            self.update_label(position)

    def set_action_label(self, position: str, label: "KeyLabel", update: bool = True):
        if label is None:
            label = self.action_labels[position]
            label.clear_values()
        else:
            self.action_labels[position] = label

        self.update_label_editor()
        if update:
            self.update_label(position)

    def update_label_editor(self):
        if not recursive_hasattr(gl, "app.main_win.sidebar.active_identifier"):
            return
        
        if gl.app.main_win.sidebar.active_identifier != self.controller_input.identifier:
            return
        
        controller = gl.app.main_win.get_active_controller()
        if controller is not self.controller_input.deck_controller:
            return

        gl.app.main_win.sidebar.key_editor.label_editor.load_for_identifier(self.controller_input.identifier, self.controller_input.state)
        

    def get_use_page_label_properties(self, position: str) -> dict:
        if self.page_labels.get(position) is None:
            return {
                "text": False,
                "color": False,
                "font-family": False,
                "font-size": False,
                "font-weight": False,
                "font-style": False,
                "outline_width": False,
                "outline_color": False,
            }
        return {
            "text": self.page_labels[position].text is not None,
            "color": self.page_labels[position].color is not None,
            "font-family": self.page_labels[position].font_name is not None,
            "font-size": self.page_labels[position].font_size is not None,
            "font-weight": self.page_labels[position].font_weight is not None,
            "font-style": self.page_labels[position].style is not None,
            "outline_width": self.page_labels[position].outline_width is not None,
            "outline_color": self.page_labels[position].outline_color is not None,
        }

    def get_composed_label(self, position: str) -> str:
        use_page_label_properties = self.get_use_page_label_properties(position)
        
        label = copy(self.action_labels.get(position)) or KeyLabel(self.controller_input)

        # Set to page values
        page_label = self.page_labels.get(position)
        if page_label is not None:
            if use_page_label_properties["text"]:
                label.text = page_label.text
            if use_page_label_properties["color"]:
                label.color = page_label.color
            if use_page_label_properties["font-family"]:
                label.font_name = page_label.font_name
            if use_page_label_properties["font-size"]:
                label.font_size = page_label.font_size
            if use_page_label_properties["font-weight"]:
                label.font_weight = page_label.font_weight
            if use_page_label_properties["font-style"]:
                label.style = page_label.style
            if use_page_label_properties["outline_width"]:
                label.outline_width = page_label.outline_width
            if use_page_label_properties["outline_color"]:
                label.outline_color = page_label.outline_color

        injected = self.inject_defaults(label)
        return self.fix_invalid(injected)
    
    def get_composed_labels(self) -> dict:
        composed_labels = {}
        for position in ["top", "center", "bottom"]:
            composed_labels[position] = self.get_composed_label(position)
        return composed_labels

    
    def inject_defaults(self, label: "KeyLabel"):
        if label.text is None:
            label.text = ""
        if label.color is None:
            label.color = gl.settings_manager.font_defaults.get("font-color", [255, 255, 255, 255])
        if label.font_name is None:
            label.font_name = gl.settings_manager.font_defaults.get("font-family", gl.FALLBACK_FONT)
        if label.font_size is None:
            label.font_size = round(gl.settings_manager.font_defaults.get("font-size", 15))
        if label.font_weight is None:
            label.font_weight = round(gl.settings_manager.font_defaults.get("font-weight", 400))
        if label.style is None:
            label.style = gl.settings_manager.font_defaults.get("font-style", "normal")
        if label.outline_width is None:
            label.outline_width = round(gl.settings_manager.font_defaults.get("outline-width", 2))
        if label.outline_color is None:
            label.outline_color = gl.settings_manager.font_defaults.get("outline-color", [0, 0, 0, 255])

        return label
    
    def fix_invalid(self, label: "KeyLabel"):
        if not isinstance(label.text, str):
            label.text = str(label.text)

        return label

    def update_label(self, position: str):
        self.controller_input.update()

    def add_labels_to_image(self, image: Image.Image) -> Image.Image:
        # image = image.rotate(self.deck.get_rotation()*-1)
        draw = ImageDraw.Draw(image)

        labels = self.get_composed_labels()
        for label in labels:
            text = labels[label].text
            if text in [None, ""]:
                continue

            font_path = labels[label].get_font_path()
            color = tuple(labels[label].color)
            font_size = labels[label].font_size
            font = ImageFont.truetype(font_path, font_size)
            outline_width = labels[label].outline_width
            outline_color = tuple(labels[label].outline_color)

            _, _, w, h = draw.textbbox((0, 0), text, font=font)

            if label == "top":
                position = (image.width / 2, h/2 + 3)
            elif label == "bottom":
                position = (image.width / 2, image.height - h/2 - 3)
            else:
                position = ((image.width - 0) / 2, (image.height - 0) / 2)

            draw.text(position,
                      text=text, font=font, anchor="mm", align="center",
                      fill=color, stroke_width=outline_width,
                      stroke_fill=outline_color)

        del draw

        return image.copy()
        # return image.copy().rotate(self.deck.get_rotation())


class LayoutManager:
    def __init__(self, controller_input: "ControllerInput"):
        self.controller_input = controller_input

        self.action_layout = ImageLayout()
        self.page_layout = ImageLayout()

    def clear(self):
        self.action_layout = ImageLayout()
        self.page_layout = ImageLayout()

    def get_use_page_layout_properties(self) -> dict:
        return {
            "valign": self.page_layout.valign is not None,
            "halign": self.page_layout.halign is not None,
            "fill-mode": self.page_layout.fill_mode is not None,
            "size": self.page_layout.size is not None
        }
    
    def get_composed_layout(self) -> ImageLayout:
        use_page_layout_properties = self.get_use_page_layout_properties()
        
        layout = copy(self.action_layout) or ImageLayout()

        # Set to page values
        page_layout = self.page_layout
        if use_page_layout_properties["valign"]:
            layout.valign = page_layout.valign
        if use_page_layout_properties["halign"]:
            layout.halign = page_layout.halign
        if use_page_layout_properties["fill-mode"]:
            layout.fill_mode = page_layout.fill_mode
        if use_page_layout_properties["size"]:
            layout.size = page_layout.size

        return self.inject_defaults(layout)
    
    def inject_defaults(self, layout: ImageLayout):
        if layout.valign is None:
            layout.valign = 0
        if layout.halign is None:
            layout.halign = 0
        if layout.fill_mode is None:
            if isinstance(self.controller_input.identifier, Input.Key):
                layout.fill_mode = "cover"
            else:
                layout.fill_mode = "contain"
        if layout.size is None:
            layout.size = 1

        return layout
    
    def set_page_layout(self, layout: ImageLayout, update: bool = True):
        self.page_layout = layout

        if update:
            self.update()

    def set_action_layout(self, layout: ImageLayout, update: bool = True):
        self.action_layout = layout

        if update:
            self.update()

    def update(self):
        self.controller_input.update()
        self.update_layout_editor()

    def update_layout_editor(self):
        if not recursive_hasattr(gl, "app.main_win.leftArea.deck_stack"):
            return
        
        if gl.app.main_win.sidebar.active_identifier != self.controller_input.identifier:
            return

        controller = gl.app.main_win.get_active_controller()
        if controller is not self.controller_input.deck_controller:
            return

        gl.app.main_win.sidebar.key_editor.image_editor.load_for_identifier(self.controller_input.identifier, self.controller_input.state)

    def add_image_to_background(self, image: Image.Image, background: Image.Image) -> Image.Image:
        if image is None:
            return background
        layout = self.get_composed_layout()

        width, height = background.size
        image_size = (int(width * layout.size), int(height * layout.size))

        if 0 in image_size:
            return background.copy()

        if layout.fill_mode == "stretch":
            image_resized = image.resize(image_size, Image.Resampling.HAMMING)
        elif layout.fill_mode == "cover":
            image_resized = ImageOps.cover(image, image_size, Image.Resampling.HAMMING)
        else:
            image_resized = ImageOps.contain(image, image_size, Image.Resampling.HAMMING)

        halign = layout.halign
        valign = layout.valign

        left_margin = int((background.width - image_resized.width) * (halign + 1) / 2)
        top_margin = int((background.height - image_resized.height) * (valign + 1) / 2)

        # Create an image copy for the result
        final_image = background.copy()

        # Paste the resized foreground onto the composite image at the calculated position
        if image_resized.has_transparency_data:
            final_image.paste(image_resized, (left_margin, top_margin), image_resized)
        else:
            final_image.paste(image_resized, (left_margin, top_margin))

        return final_image
    

class BackgroundManager:
    def __init__(self, controller_input: "ControllerInput"):
        self.controller_input = controller_input
        
        self.action_color: list[int] = None
        self.page_color: list[int] = None

    def set_action_color(self, color: list[int], update: bool = True) -> None:
        self.action_color = color
        if isinstance(color, list) and len(color) == 3:
            self.action_color.append(255)

        if update:
            self.update()

    def set_page_color(self, color: list[int], update: bool = True, update_ui: bool = True) -> None:
        self.page_color = color
        if isinstance(color, list) and len(color) == 3:
            self.page_color.append(255)

        if update:
            self.update(ui=update_ui)

    def update(self, ui: bool = True):
        self.controller_input.update()
        if ui:
            self.update_background_editor()

    def update_background_editor(self):
        if not recursive_hasattr(gl, "app.main_win.leftArea.deck_stack"):
            return
        
        if gl.app.main_win.sidebar.active_identifier != self.controller_input.identifier:
            return

        controller = gl.app.main_win.get_active_controller()
        if controller is not self.controller_input.deck_controller:
            return

        gl.app.main_win.sidebar.key_editor.background_editor.load_for_identifier(self.controller_input.identifier, self.controller_input.state)

    def get_color_is_set(self, color: list[int]) -> bool:
        return color not in [None, [None]*3, [None]*4]

    def get_use_page_background(self) -> dict:
        return self.get_color_is_set(self.page_color)
    
    def get_composed_color(self) -> list[int]:
        if self.get_use_page_background() and self.get_color_is_set(self.page_color):
            return self.page_color
        elif self.get_color_is_set(self.action_color):
            return self.action_color
        else:
            return [0] * 4


class ControllerInputState:
    def __init__(self, controller_input: "ControllerInput", state: int):
        self.controller_input = controller_input
        self.deck_controller = controller_input.deck_controller
        self.state = state
        self._overlay: Image.Image = None
        self.hide_overlay_timer: Timer = None

        # managers
        self.layout_manager = LayoutManager(self.controller_input)
        self.label_manager = LabelManager(self.controller_input)
        self.background_manager = BackgroundManager(self.controller_input)

        self.action_permission_manager = ActionPermissionManager(self)

    def __int__(self):
        return self.state
    
    def ready(self):
        pass

    def stop_overlay_timer(self):
        if self.hide_overlay_timer is not None:
            self.hide_overlay_timer.cancel()
            self.hide_overlay_timer = None

    def show_overlay(self, image: Image.Image, duration: int = -1):
        """
        duration: -1 for infinite
        """
        if duration == 0:
            self.stop_overlay_timer()
            self._overlay = None
            self.update()
        elif duration > 0:
            self._overlay = image
            self.update()
            self.hide_overlay_timer = Timer(duration, self.hide_error)
            self.hide_overlay_timer.start()
        else:
            self._overlay = image
            self.update()

    def hide_overlay(self):
        self._overlay = False
        self.update()

    def show_error(self, duration: int = -1):
        error_img = Image.open(os.path.join("Assets", "images", "error.png"))
        self.show_overlay(error_img, duration=duration)

    def hide_error(self):
        self.hide_overlay()

    def close_resources(self) -> None:
        pass

    def get_own_actions(self) -> list["ActionCore"]:
        if not self.deck_controller.get_alive(): return []
        active_page = self.deck_controller.active_page
        active_page = self.controller_input.deck_controller.active_page
        if active_page is None:
            return []
        if active_page.action_objects is None:
            return []
        actions = self.deck_controller.active_page.get_all_actions_for_input(self.controller_input.identifier, self.state)

        return actions

    def update(self) -> None:
        if self.controller_input.state == self.state:
            self.controller_input.update()
    
    def own_actions_update(self) -> None:
        for action in self.get_own_actions():
            if not isinstance(action, ActionCore):
                continue
            if not action.on_ready_called:
                continue
            action.load_initial_generative_ui()
            action.on_update()

    @log.catch
    def own_actions_tick(self) -> None:
        for action in self.get_own_actions():
            if not isinstance(action, ActionCore):
                continue
            if not action.on_ready_called:
                continue
            action.on_tick()

    @log.catch
    def own_actions_event_callback(self, event: InputEvent, data: dict = None, show_notifications: bool = False) -> None:
        for action in self.get_own_actions():
            if isinstance(action, ActionOutdated):
                if show_notifications:
                    plugin_id = gl.plugin_manager.get_plugin_id_from_action_id(action.id)
                    gl.app.send_outdated_plugin_notification(plugin_id)
                continue
            if isinstance(action, NoActionHolderFound):
                if show_notifications:
                    plugin_id = gl.plugin_manager.get_plugin_id_from_action_id(action.id)
                    gl.app.send_missing_plugin_notification(plugin_id)
                continue

            # parsed_event = event
            # if action.allow_event_configuration:
                # parsed_event = action.event_manager.get_event_assigner_for_event(event)

            if event is None:
                continue

            if not isinstance(action, ActionCore):
                continue

            action._raw_event_callback(event, data)

    def own_actions_ready_threaded(self) -> None:
        threading.Thread(target=self.own_actions_ready, name="own_actions_ready").start()

    def own_actions_update_threaded(self) -> None:
        threading.Thread(target=self.own_actions_update, name="own_actions_update").start()

    def own_actions_tick_threaded(self) -> None:
        threading.Thread(target=self.own_actions_tick, name="own_actions_tick").start()

    def own_actions_event_callback_threaded(self, event: InputEvent, data: dict = None, show_notifications: bool = False) -> None:
        threading.Thread(target=self.own_actions_event_callback, args=(event, data, show_notifications), name="own_actions_event_callback").start()

    def remove_media(self) -> None:
        page = self.controller_input.deck_controller.active_page
        if page is None:
            return

        page.set_media_path(identifier=self.controller_input.identifier, state=self.state, path=None)

        self.update()


class ControllerInput:
    def __init__(self, deck_controller: DeckController, state_class: ControllerInputState, identifier: InputIdentifier):
        self.deck_controller = deck_controller
        self.state = 0
        self.hide_error_timer: Timer = None
        self.hold_start_timer: Timer = None
        self.ControllerStateClass = state_class
        self.identifier: InputIdentifier = identifier

        self.is_visual: bool = True

        self.enable_states: bool = True

        self.states: dict[int, ControllerInputState] = {
            0: self.ControllerStateClass(self, 0),
        }

        self.states[self.state].ready()

    @staticmethod
    def Available_Identifiers(deck):
        raise AttributeError

    def update(self) -> None:
        pass

    def event_callback(self) -> None:
        pass

    def start_hold_timer(self):
        self.stop_hold_timer()

        self.hold_start_timer = threading.Timer(self.deck_controller.hold_time, self.on_hold_timer_end)
        self.hold_start_timer.setDaemon(True)
        self.hold_start_timer.setName("HoldTimer")
        self.hold_start_timer.start()

    def stop_hold_timer(self):
        if self.hold_start_timer is None:
            return
        
        self.hold_start_timer.cancel()
        self.hold_start_timer = None

    def create_n_states(self, n: int):
        if not self.enable_states:
            n = 1

        for state in self.states.values():
            state.close_resources()
        self.states.clear()

        for i in range(n):
            self.states[i] = self.ControllerStateClass(self, i)

    def load_from_page(self, page: Page):
        input_dict = self.identifier.get_config(page)
        self.load_from_input_dict(input_dict)

    def load_from_input_dict(self, page_dict, update: bool = True):
        pass

    def add_new_state(self, switch: bool = True):
        if not self.enable_states:
            if len(self.states) >= 1:
                return
            
        d = self.identifier.get_config(self.deck_controller.active_page)

        # Add new state
        self.states[len(self.states)] = self.ControllerStateClass(self, len(self.states))
        # Write to json
        for state in self.states.keys():
            d["states"].setdefault(str(state), {})

        self.deck_controller.active_page.save()
        gl.page_manager.update_dict_of_pages_with_path(self.deck_controller.active_page.json_path)

        self.update_state_switcher()

        if switch:
            log.info(f"Switching to state: {len(self.states)-1}")
            self.set_state(len(self.states)-1)

    def remove_state(self, state: int):
        d = self.identifier.get_config(self.deck_controller.active_page)

        if str(state) in d["states"]:
            d["states"].pop(str(state))

        old_loaded_state = int(self.state)

        state_to_remove = self.states.get(state)
        if state_to_remove:
            state_to_remove.close_resources()
            self.states.pop(state)

        # Fill gaps in self.states
        sorted_state_keys = sorted(self.states.keys())

        new_states = {}
        state_map = {}
        for new_key, old_key in enumerate(sorted_state_keys):
            state_map[old_key] = new_key
            self.states[old_key].state = new_key

            if self.get_active_state() is self.states[old_key]:
                self.state = new_key

            new_states[new_key] = self.states[old_key]

        self.states = new_states

        new_states_dict = {}
        for new_key, old_key in enumerate(d["states"].keys()):
            new_states_dict[str(new_key)] = d["states"][old_key]

        d["states"] = new_states_dict


        self.deck_controller.active_page.save()
        gl.page_manager.update_dict_of_pages_with_path(self.deck_controller.active_page.json_path)

        self.update_state_switcher()

        # Update - TODO: test
        if state == self.state:
            sort = sorted(list(self.states.keys()))
            sort.reverse()
            for s in sort:
                if s <= state:
                    self.set_state(s, allow_reload=True)
                    break

        gl.signal_manager.trigger_signal(Signals.RemoveState, state, state_map)

    def update_state_switcher(self):
        if gl.app.main_win.sidebar.active_identifier != self.identifier:
            return

        gl.app.main_win.sidebar.key_editor.state_switcher.set_n_states(len(self.states))

    def get_active_state(self) -> "ControllerInputState":
        return self.states.get(self.state, self.ControllerStateClass(self, -1))

    def set_state(self, state: int, update_sidebar: bool = True, allow_reload: bool = False) -> None:
        if state == self.state and not allow_reload:
            return
        
        if state not in self.states:
            log.error(f"Invalid state: {state}, must be one of {list(self.states.keys())}")
            return
        self.state = state

        self.get_active_state().update()

        if update_sidebar:
            self.reload_sidebar()

    def reload_sidebar(self) -> None:
        visible_child = gl.app.main_win.leftArea.deck_stack.get_visible_child()
        if visible_child is None:
            return
        controller = visible_child.deck_controller
        if controller is None:
            return
        
        if controller is not self.deck_controller:
            return
        if self.identifier != gl.app.main_win.sidebar.active_identifier:
            return
        
        gl.app.main_win.sidebar.active_state = self.state
        GLib.idle_add(gl.app.main_win.sidebar.update)

    def load_from_config(self, config, update: bool = True):
        n_states = len(config.get("states", {}))
        self.create_n_states(max(1, n_states))

        old_state_index = self.state

        self.state = 0

        #TODO: Reset states
        for state in config.get("states", {}):
            state: ControllerKeyState = self.states.get(int(state))
            if state is None:
                continue

            state_dict = config["states"][str(state.state)]

            self.get_active_state().own_actions_ready()
            # state.own_actions_ready() # Why not threaded? Because this would mean that some image changing calls might get executed after the next lines which blocks custom assets

            if update:
                self.set_state(old_state_index)
                self.update()

    def clear(self, update: bool = True):
        active_state = self.get_active_state()
        active_state.clear()
        if update:
            self.update()

    def has_unavailable_action(self) -> bool:
        for action in self.get_active_state().get_own_actions():
            if isinstance(action, ActionOutdated):
                return True
            if isinstance(action, NoActionHolderFound):
                return True
            
        return False
    
    def get_empty_background(self) -> Image.Image:
        pass

    def get_image_size(self) -> tuple[int, int]:
        pass

class ControllerKey(ControllerInput):
    def __init__(self, deck_controller: DeckController, ident: Input.Key):
        super().__init__(deck_controller, ControllerKeyState, ident)
        self.index = ident.get_index(deck_controller)
        # Keep track of the current state of the key because self.deck_controller.deck.key_states seams to give inverted values in get_current_deck_image
        self.press_state: bool = self.deck_controller.deck.key_states()[self.index]

        self.down_start_time: float = None

    def on_hold_timer_end(self):
        state = self.get_active_state()
        state.own_actions_event_callback_threaded(
            event=Input.Key.Events.HOLD_START
        )

    @staticmethod
    def Available_Identifiers(deck):
        return map(lambda x: f"{x[0]}x{x[1]}", map(lambda x: ControllerKey.Index_To_Coords(deck, x), range(deck.key_count())))

    @staticmethod
    def Index_To_Coords(deck, index):
        rows, cols = deck.key_layout()    
        y = index // cols
        x = index % cols
        return x, y
    
    @staticmethod
    def Coords_To_Index(deck, coords):
        if type(coords) == str:
            coords = coords.split("x")
        x, y = map(int, coords)
        rows, cols = deck.key_layout()
        return y * cols + x

    def update(self):
        image = self.get_current_image()
        rgb_image = image.convert("RGB").rotate(self.deck_controller.deck.get_rotation())

        if self.deck_controller.is_visual():
            native_image = PILHelper.to_native_key_format(self.deck_controller.deck, rgb_image)
            rgb_image.close()
            self.deck_controller.media_player.add_image_task(self.index, native_image)

        del rgb_image
        self.set_ui_key_image(image)

    def event_callback(self, press_state):
        screensaver_was_showing = self.deck_controller.screen_saver.showing
        if press_state:
            # Only on key down this allows plugins to control screen saver without directly deactivating it
            self.deck_controller.screen_saver.on_key_change()
        if screensaver_was_showing:
            return
        
        self.deck_controller.mark_page_ready_to_clear(False)
        self.press_state = press_state

        self.update()

        active_state = self.get_active_state()
        if press_state: # Key down
            self.down_start_time = time.time()
            self.start_hold_timer()
            active_state.own_actions_event_callback_threaded(
                event=Input.Key.Events.DOWN,
                show_notifications=True
            )

        elif self.down_start_time is not None: # Key up
            if time.time() - self.down_start_time >= self.deck_controller.hold_time:
                active_state.own_actions_event_callback_threaded(
                    event=Input.Key.Events.HOLD_STOP
                )
            else:
                active_state.own_actions_event_callback_threaded(
                    event=Input.Key.Events.SHORT_UP
                )
            self.down_start_time = None
            self.stop_hold_timer()
            active_state.own_actions_event_callback_threaded(
                event=Input.Key.Events.UP,
                show_notifications=False
            )
        self.deck_controller.mark_page_ready_to_clear(True)

    def get_current_image(self) -> Image.Image:
        state = self.get_active_state()

        background_color = self.get_active_state().background_manager.get_composed_color()

        background: Image.Image = None
        # Only load the background image if it's not gonna be hidden by the background color
        if background_color[-1] < 255:
            background = copy(self.deck_controller.background.tiles[self.index])

        if background_color[-1] > 0:
            background_color_img = Image.new("RGBA", self.deck_controller.get_key_image_size(), color=tuple(background_color))
            
            if background is None:
                # Use the color as the only background - happens if background color alpha is 255
                background = background_color_img
            else:
                background.paste(background_color_img, (0, 0), background_color_img)


        if background is None:
            background = self.deck_controller.generate_alpha_key().copy()

        if state._overlay:
            height = round(self.deck_controller.get_key_image_size()[1]*0.75)
            img = state._overlay.resize((height, height))
            background.paste(img, (int((self.deck_controller.get_key_image_size()[0] - height) // 2), int((self.deck_controller.get_key_image_size()[1] - height) // 2)), img)
            return background


        key_image: Image.Image = None
        # rotation = self.deck_controller.get_deck_settings().get("rotation", {}).get("value", 0)
        if state.key_image is not None:
            image = state.key_image.get_raw_image()
            key_image = state.layout_manager.add_image_to_background(
                image=image,
                background=background
            )
        elif state.key_video is not None:
            image = state.key_video.get_raw_image()
            key_image = state.layout_manager.add_image_to_background(
                image=image,
                background=background)
        else:
            key_image = background

        labeled_image = state.label_manager.add_labels_to_image(key_image)

        if self.is_pressed():
            labeled_image = self.shrink_image(labeled_image)

        if self.has_unavailable_action() and not self.deck_controller.screen_saver.showing:
            labeled_image = self.add_warning_point(labeled_image)

        if background is not None:
            background.close()

        key_image.close()

        return labeled_image
    
    def add_warning_point(self, image: Image.Image, margin: int = 10, size: int = 10, color: tuple = (255, 150, 80)) -> Image.Image:
        draw = ImageDraw.Draw(image)

        # Calculate the coordinates of the top right circle
        width, height = image.size
        top_right_x = width - margin - size
        top_right_y = margin

        # Draw the circle
        draw.ellipse((top_right_x, top_right_y, top_right_x + size, top_right_y + size), fill=color, outline=(0, 0, 0), width=2)

        del draw
        return image
    

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
    
    def load_from_input_dict(self, input_dict, update: bool = True, load_labels: bool = True, load_media: bool = True, load_background_color: bool = True):
        """
        Attention: Disabling load_media might result into disabling custom user assets
        """
        n_states = len(input_dict.get("states", {}))
        self.create_n_states(max(1, n_states))

        old_state_index = self.state

        self.state = 0

        #TODO: Reset states
        for state in input_dict.get("states", {}):
            state: ControllerKeyState = self.states.get(int(state))
            if state is None:
                continue

            state_dict = input_dict["states"][str(state.state)]

            ## Load media - why here? so that it doesn't overwrite the images chosen by the actions
            if load_media:
                state.key_image = None
                state.key_video = None
            
            if load_labels:
                state.label_manager.clear_labels()

            # Reset action layout
            layout = ImageLayout()
            state.layout_manager.set_action_layout(layout, update=False)

            state.own_actions_update() # Why not threaded? Because this would mean that some image changing calls might get executed after the next lines which blocks custom assets

            ## Load labels
            if load_labels:
                for label in state_dict.get("labels", []):
                    key_label = KeyLabel(
                        controller_input=self,
                        text=state_dict["labels"][label].get("text"),
                        font_size=state_dict["labels"][label].get("font-size"),
                        font_name=state_dict["labels"][label].get("font-family"),
                        color=state_dict["labels"][label].get("color"),
                        outline_width=state_dict["labels"][label].get("outline_width"),
                        outline_color=state_dict["labels"][label].get("outline_color")
                    )
                    # self.add_label(key_label, position=label, update=False)
                    state.label_manager.set_page_label(label, key_label, update=False)

            ## Load media
            if load_media:
                path = state_dict.get("media", {}).get("path", None)
                if path not in ["", None]:
                    if is_image(path):
                        with Image.open(path) as image:
                            state.set_image(InputImage(
                                controller_input=self,
                                image=image.copy()
                            ), update=False)
                            
                    elif is_svg(path):
                        img = svg_to_pil(path, 192)
                        state.set_image(InputImage(
                            controller_input=self,
                            image=img
                        ), update=False)

                    elif is_video(path):
                        if os.path.splitext(path)[1].lower() == ".gif":
                            state.set_video(KeyGIF(
                                controller_key=self,
                                gif_path=path,
                                loop=state_dict.get("media", {}).get("loop", True),
                                fps=state_dict.get("media", {}).get("fps", 30)
                            )) # GIFs always update
                        else:
                            state.set_video(InputVideo(
                                controller_input=self,
                                video_path=path,
                                loop = state_dict.get("media", {}).get("loop", True),
                                fps = state_dict.get("media", {}).get("fps", 30),
                            )) # Videos always update

                layout = ImageLayout(
                    fill_mode=state_dict.get("media", {}).get("fill-mode"),
                    size=state_dict.get("media", {}).get("size"),
                    valign=state_dict.get("media", {}).get("valign"),
                    halign=state_dict.get("media", {}).get("halign"),
                )
                state.layout_manager.set_page_layout(layout, update=False)

            elif len(state.get_own_actions()) > 1 and False: # Disabled for now - we might reuse it later
                if state_dict.get("image-control-action") is None:
                    with Image.open(os.path.join("Assets", "images", "multi_action.png")) as image:
                        self.set_key_image(InputImage(
                            controller_input=self,
                            image=image.copy(),
                        ), update=False)
            
            elif len(state.get_own_actions()) == 1:
                if state_dict.get("image-control-action") is None:
                    self.set_key_image(None, update=False)
                # action = self.get_own_actions()[0]
                # if action.has_image_control()

            if load_background_color:
                state.background_manager.set_page_color(state_dict.get("background", {}).get("color"), update=False)

        if update:
            self.set_state(old_state_index)
            self.update()

    def set_state(self, state: int, update_sidebar: bool = True, allow_reload: bool = False) -> None:
        old_state = self.state
        if state == old_state and not allow_reload:
            return
        super().set_state(state, False, allow_reload)
        if update_sidebar:
            self.reload_sidebar()

    def set_ui_key_image(self, image: Image.Image) -> None:
        if image is None:
            return
        
        x, y = ControllerKey.Index_To_Coords(self.deck_controller.deck, self.index)

        if self.deck_controller.get_own_key_grid() is None or not gl.app.main_win.get_mapped():
            # Save to use later
            self.deck_controller.ui_image_changes_while_hidden[self.identifier] = image # The ui key coords are in reverse order
        else:
            try:
                self.deck_controller.get_own_key_grid().buttons[x][y].set_image(image)
            except:
                print(f"Failed to set ui key image for {self.identifier}")
        
    def get_own_ui_key(self) -> KeyButton:
        x, y = ControllerKey.Index_To_Coords(self.deck_controller.deck, self.index)
        buttons = self.deck_controller.get_own_key_grid().buttons # The ui key coords are in reverse order
        return buttons[x][y]
    
    def get_image_size(self) -> tuple[int, int]:
        return self.deck_controller.get_key_image_size()

class ControllerTouchScreen(ControllerInput):
    def __init__(self, deck_controller: DeckController, ident: InputIdentifier):
        super().__init__(deck_controller, ControllerTouchScreenState, ident)

        self.enable_states = False

    @staticmethod
    def Available_Identifiers(deck):
        if deck.is_touch():
            return ["sd-plus"]
        return []

    def update(self) -> None:
        image = self.get_current_image()
        rgb_image = image.convert("RGB")
        native_image = PILHelper.to_native_touchscreen_format(self.deck_controller.deck, rgb_image)
        rgb_image.close()
        self.deck_controller.media_player.add_touchscreen_task(native_image)

        del rgb_image
        self.set_ui_image(image)

    def generate_empty_image(self) -> Image.Image:
        return Image.new("RGBA", self.get_screen_dimensions(), (0, 0, 0, 0))
    
    def get_dial_image_area(self, identifier: Input.Dial) -> tuple[int, int, int, int]:
        width, height = self.get_screen_dimensions()

        n_dials = len(self.deck_controller.inputs[Input.Dial])
        dial_index = identifier.index

        start_x = int((dial_index / n_dials) * width)
        start_y = 0
        end_x = int(((dial_index + 1) / n_dials) * width)
        end_y = height

        return start_x, start_y, end_x, end_y
    
    def get_dial_image_area_size(self) -> tuple[int, int]:
        width, height = self.get_screen_dimensions()

        n_dials = len(self.deck_controller.inputs[Input.Dial])

        return int(width / n_dials), height
    
    def get_empty_dial_image(self) -> Image.Image:
        screen_width, screen_height = self.get_screen_dimensions()

        n_dials = len(self.deck_controller.inputs[Input.Dial])

        return Image.new("RGBA", (screen_width // n_dials, screen_height), (0, 0, 0, 0))

    def set_ui_image(self, image: Image.Image) -> None:
        if recursive_hasattr(self, "deck_controller.own_deck_stack_child.page_settings.deck_config.screenbar.image") and gl.app.main_win.get_mapped():
            screenbar = self.deck_controller.own_deck_stack_child.page_settings.deck_config.screenbar
            screenbar.image.set_image(image)
        else:
            self.deck_controller.ui_image_changes_while_hidden[self.identifier] = image

    def get_current_image(self) -> Image.Image:
        active_state = self.get_active_state()
        return active_state.get_current_image()

    def event_callback(self, event_type, value):
        screensaver_was_showing = self.deck_controller.screen_saver.showing
        if event_type in (TouchscreenEventType.SHORT, TouchscreenEventType.LONG, TouchscreenEventType.DRAG):
            self.deck_controller.screen_saver.on_key_change()
        if screensaver_was_showing:
            return
        
        active_state = self.get_active_state()
        if event_type == TouchscreenEventType.DRAG:
            # Check if from left to right or the other way
            if value['x'] > value['x_out']:
                active_state.own_actions_event_callback_threaded(
                    Input.Touchscreen.Events.DRAG_LEFT
                )
            else:
                active_state.own_actions_event_callback_threaded(
                    Input.Touchscreen.Events.DRAG_RIGHT
                )


        #TODO get matching actions from the dials
        elif event_type in (TouchscreenEventType.SHORT, TouchscreenEventType.LONG):
            dial = self.get_dial_for_touch_x(value['x'])
            if dial is not None:
                dial_active_state = dial.get_active_state()
                if dial_active_state is not None:

                    event = Input.Dial.Events.SHORT_TOUCH_PRESS
                    if event_type == TouchscreenEventType.LONG:
                        event = Input.Dial.Events.LONG_TOUCH_PRESS

                    dial_active_state.own_actions_event_callback_threaded(
                        event,
                        data={"x": value['x'], "y": value['y']},
                        show_notifications=True
                    )

    def get_dial_for_touch_x(self, touch_x: float) -> "ControllerDial":
        screen_width = self.deck_controller.get_touchscreen_image_size()[0]
        n_dials = len(self.deck_controller.inputs[Input.Dial])
        dial_index = int((touch_x / screen_width) * n_dials)

        return self.deck_controller.get_input(Input.Dial(str(dial_index)))
    
    def get_screen_dimensions(self) -> tuple[int, int]:
        return self.deck_controller.get_touchscreen_image_size()

class ControllerDial(ControllerInput):
    def __init__(self, deck_controller: DeckController, ident: InputIdentifier):
        super().__init__(deck_controller, ControllerDialState, ident)

        self.down_start_time: float = None

    def on_hold_timer_end(self):
        state = self.get_active_state()
        state.own_actions_event_callback_threaded(
            event=Input.Dial.Events.HOLD_START
        )

    def get_touch_screen(self) -> ControllerTouchScreen:
        return self.deck_controller.get_input(Input.Touchscreen("sd-plus"))

    @staticmethod
    def Available_Identifiers(deck):
        return map(str, range(deck.dial_count()))

    def event_callback(self, event_type, value):
        screensaver_was_showing = self.deck_controller.screen_saver.showing
        if event_type == DialEventType.TURN:
            self.deck_controller.screen_saver.on_key_change()
        if event_type == DialEventType.PUSH and value:
            # Only on push, not on hold to allow actions to enable the screensaver without directly causing it to wake up again
            self.deck_controller.screen_saver.on_key_change()
        if screensaver_was_showing:
            return
        
        active_state = self.get_active_state()
        if event_type == DialEventType.PUSH:
            if value:
                self.down_start_time = time.time()
                self.start_hold_timer()
                active_state.own_actions_event_callback_threaded(
                    event=Input.Dial.Events.DOWN,
                    show_notifications=True
                )
            elif self.down_start_time is not None:
                self.stop_hold_timer()
                if time.time() >= self.down_start_time + self.deck_controller.hold_time:
                    active_state.own_actions_event_callback_threaded(
                        event=Input.Dial.Events.HOLD_STOP
                    )
                else:
                    active_state.own_actions_event_callback_threaded(
                        event=Input.Dial.Events.SHORT_UP
                    )
                self.down_start_time = None
                active_state.own_actions_event_callback_threaded(
                    event=Input.Dial.Events.UP
                )
        
        elif event_type == DialEventType.TURN:
            if value < 0:
                active_state.own_actions_event_callback_threaded(
                    event=Input.Dial.Events.TURN_CCW
                )
            else:
                active_state.own_actions_event_callback_threaded(
                    event=Input.Dial.Events.TURN_CW
                )

    def load_from_input_dict(self, page_dict, update: bool = True):
        n_states = len(page_dict.get("states", {}))
        self.create_n_states(max(1, n_states))

        old_state_index = self.state

        self.state = 0

        for state in page_dict.get("states", {}):
            state: ControllerDialState = self.states.get(int(state))
            if state is None:
                continue

            state_dict = page_dict["states"][str(state.state)]

            # Reset action layout
            layout = ImageLayout()
            state.layout_manager.set_action_layout(layout, update=False)

            state.own_actions_update() # Why not threaded? Because this would mean that some image changing calls might get executed after the next lines which blocks custom assets

            ## Load labels
            for label in state_dict.get("labels", []):
                key_label = KeyLabel(
                    controller_input=self,
                    text=state_dict["labels"][label].get("text"),
                    font_size=state_dict["labels"][label].get("font-size"),
                    font_name=state_dict["labels"][label].get("font-family"),
                    color=state_dict["labels"][label].get("color"),
                )
                state.label_manager.set_page_label(label, key_label, update=False)

            ## Load media
            path = state_dict.get("media", {}).get("path")
            if path not in ["", None]:
                if is_image(path):
                    image = InputImage(
                        controller_input=self,
                        image=Image.open(path),
                    )
                    state.set_image(image, update=False)
                elif is_svg(path):
                    img = svg_to_pil(path, 192)
                    state.set_image(InputImage(
                        controller_input=self,
                        image=img
                    ), update=False)

                elif is_video(path):
                    if os.path.splitext(path)[1].lower() == ".gif":
                        raise NotImplementedError("TODO") #TODO
                        state.set_video(KeyGIF(
                            controller_key=self,
                            gif_path=path,
                            loop=state_dict.get("media", {}).get("loop", True),
                            fps=state_dict.get("media", {}).get("fps", 30)
                        )) # GIFs always update
                    else:
                        state.set_video(InputVideo(
                            controller_input=self,
                            video_path=path,
                            loop = state_dict.get("media", {}).get("loop", True),
                            fps = state_dict.get("media", {}).get("fps", 30),
                        )) # Videos always update

            layout = ImageLayout(
                fill_mode=state_dict.get("media", {}).get("fill-mode"),
                size=state_dict.get("media", {}).get("size"),
                valign=state_dict.get("media", {}).get("valign"),
                halign=state_dict.get("media", {}).get("halign"),
            )
            state.layout_manager.set_page_layout(layout, update=False)

            state.background_manager.set_page_color(state_dict.get("background", {}).get("color", [0, 0, 0, 0]), update=False)

        if update:
            self.set_state(old_state_index)
            self.update()

    def update(self):
        self.get_touch_screen().update()

    def get_image_size(self) -> tuple[int, int]:
        return self.get_touch_screen().get_dial_image_area_size()
    

class ControllerTouchScreenState(ControllerInputState):
    def __init__(self, controller_touch: "ControllerTouchScreen", state: int):
        super().__init__(controller_touch, state)

        self.controller_touch = controller_touch

    def set_current_image(self, image: Image.Image):
        self.current_image = image

        self.update()

    def get_current_image(self) -> Image.Image:
        background = self.controller_touch.generate_empty_image()

        for dial in self.controller_touch.deck_controller.inputs[Input.Dial]:
            state = dial.get_active_state()
            image_area = self.controller_touch.get_dial_image_area(dial.identifier)
            dial_image = state.get_rendered_touch_image()

            background.paste(dial_image, image_area, dial_image)

        return background


    def update(self):
        if self.controller_touch.get_active_state() is self:
            self.controller_touch.update()

    

    def set_dial_image(self, identifier: Input.Dial, image: Image.Image, update: bool = True):
        return
        assert isinstance(identifier, Input.Dial)

        area = self.get_dial_image_area(identifier)
        width, height = area[2] - area[0], area[3] - area[1]

        # Clear underground
        self.current_image.paste(self.get_empty_dial_image(), area)

        # Contain image into the area
        image = ImageOps.contain(image, (width, height), Image.Resampling.HAMMING)

        # Get x, y for centered position
        x = area[0] + int((width - image.width) / 2)
        y = area[1] + int((height - image.height) / 2)

        self.current_image.paste(image, (x, y), image)

        self.current_image.save("sd.png")

        if update:
            self.update()


    def clear(self):
        self.set_current_image(self.controller_touch.generate_empty_image())

    def close_resources(self) -> None:
        self.current_image.close()
        del self.current_image

class ControllerDialState(ControllerInputState):
    def __init__(self, dial: "ControllerDial", state: int):
        self.dial = dial

        self.image: InputImage = None
        self.video: InputVideo = None

        self.touch_image: Image.Image = None

        super().__init__(dial, state)

    def set_image(self, image: "InputImage", update: bool = True) -> None:
        if self.image is not None:
            self.image.close()

        self.image = image

        if update:
            self.update()

    def set_video(self, video: "InputVideo") -> None:
        if self.video is not None:
            self.video.close()

        self.video = video


    def get_rendered_touch_image(self) -> Image.Image:
        touch_screen = self.dial.get_touch_screen()

        background: Image.Image = None

        background_color = self.background_manager.get_composed_color()

        if background_color[-1] < 255:
            background = touch_screen.get_empty_dial_image()
        if background_color[-1] > 0:
            background_color_img = Image.new("RGBA", self.dial.get_image_size(), color=tuple(background_color))

            if background is None:
                # Use the color as the only background - happens if background color alpha is 255
                background = background_color_img
            else:
                background.paste(background_color_img, (0, 0), background_color_img)
        

        image = None
        if self.video is not None:
            image = self.video.get_next_frame()
        elif self.image is not None:
            image = self.image.image

        # rotation = self.deck_controller.get_deck_settings().get("rotation", {}).get("value", 0)

        image = self.layout_manager.add_image_to_background(image, background)
        image = self.label_manager.add_labels_to_image(image)

        return image

class ControllerKeyState(ControllerInputState):
    def __init__(self, controller_key: "ControllerKey", state: int):
        super().__init__(controller_key, state)

        self.key_image: InputImage = None
        self.key_video: InputVideo = None

    def close_resources(self) -> None:
        if self.key_image is not None:
            self.key_image.close()
            self.key_image = None
        if self.key_video is not None:
            self.key_video.close()
            self.key_video = None
    
    def set_image(self, key_image: "InputImage", update: bool = True) -> None:
        if self.key_image is not None:
            self.key_image.close()

        self.key_image = key_image
        self.key_video = None

        if update:
            self.update()

    def set_video(self, key_video: "InputVideo") -> None:
        self.key_video = key_video
        if self.key_image is not None:
            self.key_image.close()
        self.key_image = None

    def clear(self):
        self.key_image = None
        self.key_video = None
        self.label_manager.clear_labels()
        self.layout_manager.clear()
        self.background_manager.set_page_color(None)