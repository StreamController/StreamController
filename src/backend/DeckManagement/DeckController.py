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
import os
import sys
import threading
import time
from functools import lru_cache
from queue import Queue
from threading import Thread
from typing import TYPE_CHECKING

from PIL import Image
from StreamDeck.Devices import StreamDeck
from StreamDeck.Devices.StreamDeckPlus import StreamDeckPlus
from StreamDeck.ImageHelpers import PILHelper
from gi.repository import GLib
from loguru import logger as log

import globals as gl
from src.backend.DeckManagement.BetterDeck import BetterDeck
from src.backend.DeckManagement.HelperMethods import recursive_hasattr
from src.backend.DeckManagement.InputIdentifier import (
    Input,
    InputEvent,
    InputIdentifier,
)
from src.backend.DeckManagement.Subclasses.Background import (
    Background,
    BackgroundImage,
    BackgroundVideo,
)
from src.backend.DeckManagement.Subclasses.ControllerDial import (
    ControllerDial,
    ControllerDialState,
)
from src.backend.DeckManagement.Subclasses.ControllerInput import (
    ControllerInput,
    ControllerInputState,
)
from src.backend.DeckManagement.Subclasses.ControllerKey import (
    ControllerKey,
    ControllerKeyState,
)
from src.backend.DeckManagement.Subclasses.ControllerTouchScreen import (
    ControllerTouchScreen,
    ControllerTouchScreenState,
)
from src.backend.DeckManagement.Subclasses.FakeDeck import FakeDeck
from src.backend.DeckManagement.Subclasses.InputStateManagers import (
    BackgroundManager,
    LabelManager,
    LayoutManager,
)
from src.backend.DeckManagement.Subclasses.KeyGIF import KeyGIF
from src.backend.DeckManagement.Subclasses.KeyLabel import KeyLabel
from src.backend.DeckManagement.Subclasses.MediaPlayer import (
    MediaPlayerSetImageTask,
    MediaPlayerSetTouchscreenImageTask,
    MediaPlayerTask,
    MediaPlayerThread,
)
from src.backend.DeckManagement.Subclasses.ScreenSaver import ScreenSaver
from src.backend.PageManagement.Page import Page
from src.Signals import Signals
from src.windows.mainWindow.elements.KeyGrid import KeyGrid

if TYPE_CHECKING:
    from src.backend.DeckManagement.DeckManager import DeckManager
    from src.windows.mainWindow.elements.DeckStackChild import DeckStackChild

__all__ = [
    "DeckController",
    "Background",
    "BackgroundImage",
    "BackgroundVideo",
    "BackgroundManager",
    "ControllerDial",
    "ControllerDialState",
    "ControllerInput",
    "ControllerInputState",
    "ControllerKey",
    "ControllerKeyState",
    "ControllerTouchScreen",
    "ControllerTouchScreenState",
    "KeyGIF",
    "KeyLabel",
    "LabelManager",
    "LayoutManager",
    "MediaPlayerSetImageTask",
    "MediaPlayerSetTouchscreenImageTask",
    "MediaPlayerTask",
    "MediaPlayerThread",
]


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
        self.has_animated_keys = False

        self.key_spacing = (36, 36)

        if isinstance(self.deck, StreamDeckPlus) or (isinstance(self.deck, FakeDeck) and self.deck.key_layout() == [2, 4]):
            log.error("Deck recognized as StreamDeckPlus")
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
        self.TICK_DELAY = 1
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
        if gl.screen_locked and gl.settings_manager.get_app_settings().get("system", {}).get("lock-on-lock-screen", True):
            self.allow_interaction = False
            self.screen_saver.show()
        else:
            self.load_default_page()

    def init_inputs(self):
        for i in Input.All:
            self.inputs[i] = []
            input_class = getattr(sys.modules[__name__], i.controller_class_name)

            for k in input_class.Available_Identifiers(self.deck):
                self.inputs[i].append(input_class(self, Input.FromTypeIdentifier(i.input_type, k)))

    def get_inputs(self, identifier: InputIdentifier) -> list["ControllerInput"]:
        input_type = type(identifier)
        if input_type not in self.inputs:
            raise ValueError(f"Unknown input type: {input_type}")
        return self.inputs[input_type]

    def get_input(self, identifier: InputIdentifier) -> "ControllerInput":
        for i in self.get_inputs(identifier):
            if i.identifier == identifier:
                return i
        return None

    @lru_cache(maxsize=None)
    def serial_number(self) -> str:
        return self.deck.get_serial_number()
    
    def is_visual(self) -> bool:
        return self.deck.is_visual()

    def update_input(self, identifier: InputIdentifier):
        i = self.get_input(identifier)
        if not i:
            return
        i.update()

    @log.catch
    def update_all_inputs(self):
        start = time.time()
        if not self.get_alive(): return
        if self.background.video is not None:
            log.debug("Skipping update_all_inputs because there is a background video -- we will only update the dials (if exists) so as not to effect the video.")

            for i in self.inputs[Input.Dial]:
                i.update()
            return
        for t in self.inputs:
            for i in self.inputs[t]:
                i.update()
        log.debug(f"Updating all inputs took {time.time() - start} seconds")

    def event_callback(self, ident: InputIdentifier, *args, **kwargs):
        if not self.allow_interaction:
            return
        i = self.get_input(ident)
        if not i:
            return
        i.event_callback(*args, **kwargs)

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
    def get_key_image_size(self) -> tuple[int]:
        if not self.get_alive(): return
        size = self.deck.key_image_format()["size"]
        if size is None:
            return (72, 72)
        size = max(size[0], 72), max(size[1], 72)
        return size
    
    @lru_cache(maxsize=None)
    def get_touchscreen_image_size(self) -> tuple[int]:
        if not self.get_alive(): return
        size = self.deck.touchscreen_image_format()["size"]
        if size is None:
            return (800, 100)
        size = max(size[0], 800), max(size[1], 100)
        return size

    # ------------ #
    # Page Loading #
    # ------------ #

    def load_default_page(self):
        if not self.get_alive(): return

        api_page_path = None
        if self.serial_number() in gl.api_page_requests:
            api_page_path = gl.api_page_requests[self.serial_number()]
            api_page_path = gl.page_manager.find_matching_page_path(api_page_path)

        if api_page_path is None:
            default_page_path = gl.page_manager.get_default_page(self.deck.get_serial_number())
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

        # Handle state change requests
        if self.serial_number() in gl.api_state_requests:
            state_request = gl.api_state_requests[self.serial_number()]
            page_name = state_request["page_name"]
            coords = state_request["coords"]
            state = state_request["state"]
            
            # Get the page path for the specified page
            requested_page_path = gl.page_manager.find_matching_page_path(page_name)
            
            if requested_page_path is None:
                # Page not found - log available pages
                available_pages = [os.path.splitext(os.path.basename(p))[0] for p in gl.page_manager.get_pages()]
                log.error(f"State change failed: Page '{page_name}' not found for device {self.serial_number()}. Available pages: {', '.join(available_pages)}")
            else:
                # Load the requested page if it's different from the current one
                if os.path.abspath(requested_page_path) != os.path.abspath(self.active_page.json_path):
                    requested_page = gl.page_manager.get_page(requested_page_path, self)
                    self.load_page(requested_page)
                
                # Parse coordinates and change state with enhanced error handling
                try:
                    x, y = map(int, coords.split(','))
                    
                    # Validate coordinates are within bounds
                    rows, cols = self.deck.key_layout()
                    if x < 0 or x >= cols or y < 0 or y >= rows:
                        log.error(f"State change failed: Coordinates ({x},{y}) out of bounds for device {self.serial_number()}. Valid range: x=0-{cols-1}, y=0-{rows-1}")
                    else:
                        identifier = Input.Key(f"{x}x{y}")
                        c_input = self.get_input(identifier)
                        
                        if c_input is None:
                            log.error(f"State change failed: No input found at coordinates ({x},{y}) on device {self.serial_number()}")
                        elif state < 0 or state >= len(c_input.states):
                            max_state = len(c_input.states) - 1
                            if max_state == 0:
                                log.error(f"State change failed: Position ({x},{y}) on device {self.serial_number()} only has 1 state (state 0). Requested state {state} does not exist")
                            else:
                                log.error(f"State change failed: Position ({x},{y}) on device {self.serial_number()} has states 0-{max_state}. Requested state {state} does not exist")
                        else:
                            # Successfully change state
                            c_input.set_state(state)
                            log.info(f"Successfully changed state of position ({x},{y}) to state {state} on device {self.serial_number()}")
                            
                except (ValueError, AttributeError) as e:
                    log.error(f"State change failed: Invalid coordinate format '{coords}' for device {self.serial_number()}. Expected format: 'x,y' (e.g., '0,0'). Exception: {e}")
                except Exception as e:
                    log.error(f"State change failed: Unexpected error for device {self.serial_number()}: {e}")
            
            # Remove the request after processing
            del gl.api_state_requests[self.serial_number()]

    @log.catch
    def load_background(self, page: Page, update: bool = True):
        deck_settings = self.get_deck_settings()

        deck_background_settings = deck_settings.get("background", {})
        page_background_settings = page.dict.get("settings", {}).get("background", {})

        log.info(f"Loading background in thread: {threading.get_ident()}")
        if deck_background_settings.get("enable", False) and not page_background_settings.get("overwrite", False):
            config = deck_background_settings
        elif page_background_settings.get("overwrite", False) and page_background_settings.get("show", False):
            config = page_background_settings
        else:
            config = {}

        self.background.set_from_path(
            path=config.get("media-path"),
            update=update,
            loop=config.get("loop", False),
            fps=config.get("fps", 30),
        )

    @log.catch
    def load_brightness(self, page: Page):
        if not self.get_alive():
            return

        deck_brightness = self.get_deck_settings().get("brightness", {})
        page_brightness = page.dict.get("settings",{}).get("brightness", {})

        if page_brightness.get("overwrite", False):
            value = page_brightness.get("value", 75)
        else:
            value = deck_brightness.get("value", 75)

        log.info(value)

        self.set_brightness(value)

    @log.catch
    def load_screensaver(self, page: Page):
        deck_settings = self.get_deck_settings()
        deck_screensaver_settings = deck_settings.get("screensaver", {})
        page_screensaver_settings = page.dict.get("settings", {}).get("screensaver", {})

        log.info(f"Loading screensaver in thread: {threading.get_ident()}")
        if deck_screensaver_settings.get("enable", False) and not page_screensaver_settings.get("overwrite", False):
            config = deck_screensaver_settings
        elif page_screensaver_settings.get("overwrite", False) and page_screensaver_settings.get("enable", False):
            config = page_screensaver_settings
        else:
            config = {}

        self.screen_saver.set_media_path(config.get("media-path"))
        self.screen_saver.set_enable(config.get("enable", False))
        self.screen_saver.set_time(config.get("time-delay", 5))
        self.screen_saver.set_loop(config.get("loop", False))
        self.screen_saver.set_fps(config.get("fps", 30))
        self.screen_saver.set_brightness(config.get("brightness", 30))

    @log.catch
    def load_all_inputs(self, page: Page, update: bool = True):
        from concurrent.futures import ThreadPoolExecutor
        start = time.time()
        with ThreadPoolExecutor() as executor:
            futures = []
            for t in self.inputs:
                for controller_input in self.inputs[t]:
                    futures.append(executor.submit(self.load_input, controller_input, page, update))
            for future in futures:
                future.result()
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

    def close_image_ressources(self):
        for t in self.inputs:
            for i in self.inputs[t]:
                i.close_resources()

        if self.background.video is not None:
            self.background.video.close()
            self.background.video = None
        if self.background.image is not None:
            self.background.image.close()
            self.background.image = None

    @log.catch
    def load_page(self, page: Page, load_brightness: bool = True, load_screensaver: bool = True, load_background: bool = True, load_inputs: bool = True, allow_reload: bool = True):
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

        old_tick = self.media_player.media_ticks
        old_time = time.time()
        while self.media_player.media_ticks <= old_tick and time.time() - old_time <= 0.5:
            time.sleep(0.05)

        # Update ui
        GLib.idle_add(self.update_ui_on_page_change) #TODO: Use new signal manager instead

        if load_background:
            # self.load_background(page, update=False)
            self.media_player.add_task(self.load_background, page, update=False)
        if load_brightness:
            self.load_brightness(page)
        if load_screensaver:
            self.load_screensaver(page)
        if load_inputs:
            self.media_player.add_task(self.load_all_inputs, page, update=False)

        self.active_page.initialize_actions()

        # Load page onto deck
        self.media_player.add_task(self.update_all_inputs)

        # Notify plugin actions
        gl.signal_manager.trigger_signal(Signals.ChangePage, self, old_path, self.active_page.json_path)

        log.info(f"Loaded page {page.get_name()} on deck {self.deck.get_serial_number()}")
        gc.collect()

    def reload_page(self):
        self.load_page(
            page=self.active_page,
            allow_reload=True
        )

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
            if not self.screen_saver.showing and True:
                for t in self.inputs:
                    for i in self.inputs[t]:
                        i.get_active_state().own_actions_tick_threaded()
            else:
                for t in self.inputs:
                    for i in self.inputs[t]:
                        i.update()

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
        
        if not recursive_hasattr(gl, "app.main_win.leftArea.deck_stack"): return
        serial_number = self.deck.get_serial_number()
        deck_stack = gl.app.main_win.leftArea.deck_stack
        deck_stack_child = deck_stack.get_child_by_name(serial_number)
        if deck_stack_child == None:
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
        if deck_stack_child == None:
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
        if hasattr(self, "active_page"):
            if self.active_page is not None:
                self.active_page.action_objects = {}

        if hasattr(self, "media_player"):
            self.media_player.stop()

        self.keep_actions_ticking = False
        self.deck.run_read_thread = False

    def get_alive(self) -> bool:
        try:
            return self.deck.is_open()
        except Exception as e:
            log.debug(f"Cougth dead deck error. Error: {e}")
            return False
