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
import hashlib
import os
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
from PIL import Image, ImageDraw, ImageFont, ImageSequence
from StreamDeck.Devices import StreamDeck
from StreamDeck.Devices.StreamDeck import DialEventType, TouchscreenEventType
from StreamDeck.Devices.StreamDeckPlus import StreamDeckPlus
from loguru import logger as log

# Import own modules
from StreamDeck.Devices.RotatedDeck import RotatedDeck
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
from src.api import notify_active_page_changed

process = psutil.Process()

from gi.repository import GLib

# Import signals
from src.Signals import Signals

# Import typing
from typing import TYPE_CHECKING, ClassVar, cast

from src.windows.mainWindow.elements.KeyGrid import KeyButton, KeyGrid
from src.backend.PluginManager.ActionCore import ActionCore
if TYPE_CHECKING:
    from src.windows.mainWindow.elements.DeckStackChild import DeckStackChild
    from src.backend.DeckManagement.DeckManager import DeckManager

# Import globals
import globals as gl

TASK_PRIORITY_LOW = 10
TASK_PRIORITY_NORMAL = 50
TASK_PRIORITY_HIGH = 100
TASK_PRIORITY_BOOST_WINDOW = 0.25


def _hash_payload(data: bytes) -> bytes:
    return hashlib.blake2b(data, digest_size=8).digest()


def _hash_image(image: Image.Image) -> bytes:
    return _hash_payload(image.tobytes())


@dataclass
class MediaPlayerTask:
    deck_controller: "DeckController"
    page: Page
    _callable: callable
    args: tuple
    kwargs: dict
    task_label: str = ""
    created_at: float = 0.0

    def run(self):
        if self.created_at == 0.0:
            self.created_at = time.time()
        self._callable(*self.args, **self.kwargs)

@dataclass
class MediaPlayerSetTouchscreenImageTask:
    deck_controller: "DeckController"
    page: Page
    image: Image.Image
    x_pos: int
    y_pos: int
    width: int
    height: int
    priority: int = TASK_PRIORITY_NORMAL
    image_hash: bytes = None

    n_failed_in_row: ClassVar[dict] = {}

    def __post_init__(self):
        if self.image_hash is None:
            self.image_hash = _hash_image(self.image)

    def region_key(self) -> tuple[int, int, int, int]:
        return (self.x_pos, self.y_pos, self.width, self.height)

    def can_merge_with(self, other: "MediaPlayerSetTouchscreenImageTask") -> bool:
        if self.page is not other.page or self.priority != other.priority:
            return False
        if self.y_pos != other.y_pos or self.height != other.height:
            return False
        return self.x_pos + self.width >= other.x_pos

    def merge_with(self, other: "MediaPlayerSetTouchscreenImageTask") -> "MediaPlayerSetTouchscreenImageTask":
        x1 = min(self.x_pos, other.x_pos)
        x2 = max(self.x_pos + self.width, other.x_pos + other.width)
        width = x2 - x1

        merged = Image.new("RGBA", (width, self.height), (0, 0, 0, 0))
        merged.paste(self.image, (self.x_pos - x1, 0))
        merged.paste(other.image, (other.x_pos - x1, 0))

        self.close()
        other.close()

        return MediaPlayerSetTouchscreenImageTask(
            deck_controller=self.deck_controller,
            page=self.page,
            image=merged,
            x_pos=x1,
            y_pos=self.y_pos,
            width=width,
            height=self.height,
            priority=self.priority,
        )

    def close(self):
        if self.image is not None:
            self.image.close()
            self.image = None

    def _get_native_image(self) -> bytes:
        image = self.image
        temporaries = []

        if image.mode == "RGBA":
            background = Image.new("RGB", image.size, (0, 0, 0))
            background.paste(image, (0, 0), image)
            image = background
            temporaries.append(background)

        # The image is rendered in logical orientation - turn it into what the
        # device expects. expand=True because, unlike keys, the strip is not square.
        rotation = self.deck_controller.deck.get_rotation()
        if rotation:
            image = image.rotate(rotation, expand=True)
            temporaries.append(image)

        try:
            return PILHelper.to_native_touchscreen_format(self.deck_controller.deck, image)
        finally:
            for temporary in temporaries:
                temporary.close()

    def run(self):
        if not self.deck_controller.deck.is_touch():
            self.close()
            return
        try:
            x_pos, y_pos, width, height = self.deck_controller.deck.logical_touch_rect_to_physical(
                self.x_pos, self.y_pos, self.width, self.height
            )
            self.deck_controller.deck.set_touchscreen_image(
                self._get_native_image(),
                x_pos=x_pos,
                y_pos=y_pos,
                width=width,
                height=height,
            )
            MediaPlayerSetTouchscreenImageTask.n_failed_in_row[self.deck_controller.serial_number()] = 0
        except StreamDeck.TransportError as e:
            log.error(f"Failed to set deck touchscreen image. Error: {e}")

            beta_resume = gl.settings_manager.get_app_settings().get("system", {}).get("beta-resume-mode", True)
            if beta_resume:
                # Transient HID failures are expected right after resume - keep the controller alive and retry
                return

            serial = self.deck_controller.serial_number()
            MediaPlayerSetTouchscreenImageTask.n_failed_in_row[serial] = MediaPlayerSetTouchscreenImageTask.n_failed_in_row.get(serial, 0) + 1
            if MediaPlayerSetTouchscreenImageTask.n_failed_in_row[serial] > 10:
                log.debug(f"Failed to set touchscreen image for 10 times in a row for deck {serial}. Removing controller")

                self.deck_controller.deck.close()
                self.deck_controller.media_player.running = False # Set stop flag - otherwise remove_controller will wait until this task is done, which it never will because it waits
                gl.deck_manager.remove_controller(self.deck_controller)

                gl.deck_manager.connect_new_decks()
        finally:
            self.close()

@dataclass
class MediaPlayerSetImageTask:
    deck_controller: "DeckController"
    page: Page
    key_index: int
    native_image: bytes
    priority: int = TASK_PRIORITY_NORMAL
    image_hash: bytes = None

    n_failed_in_row: ClassVar[dict] = {}

    def __post_init__(self):
        if self.image_hash is None:
            self.image_hash = _hash_payload(self.native_image)

    def close(self):
        self.native_image = None

    def run(self):
        try:
            self.deck_controller.deck.set_key_image(self.key_index, self.native_image)
            self.close()
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
        finally:
            self.close()


class MediaPlayerThread(threading.Thread):
    def __init__(self, deck_controller: "DeckController"):
        super().__init__(name="MediaPlayerThread", daemon=True)
        self.deck_controller: DeckController = deck_controller
        self.FPS = 30 # Max refresh rate of the internal displays

        self.running = False
        self.media_ticks = 0

        self.pause = False
        self._stop_requested = False
        self._wake_event = threading.Event()

        self.tasks: list[MediaPlayerTask] = []
        self.image_tasks = {}
        self.touchscreen_task = None
        self._wake_event = threading.Event()
        self.touchscreen_region_tasks = {}
        self.last_key_image_hashes: dict[int, bytes] = {}
        self.last_touchscreen_hashes: dict[tuple[int, int, int, int], bytes] = {}
        self.priority_boosts: dict[InputIdentifier, float] = {}

        self.fps: list[float] = []
        self.old_warning_state = False

        self.show_fps_warnings = gl.settings_manager.get_app_settings().get("warnings", {}).get("enable-fps-warnings", True)

    # @log.catch
    def run(self):
        self.running = True

        while True:
            start = time.time()

            # self.check_connection()

            has_bg_video = False

            if not self.pause:
                if self.deck_controller.background.video is not None:
                    if self.deck_controller.background.video.page is self.deck_controller.active_page:
                        has_bg_video = True
                        # There is a background video
                        video_each_nth_frame = self.FPS // self.deck_controller.background.video.fps
                        if self.media_ticks % video_each_nth_frame == 0:
                            self.deck_controller.background.update_tiles()

                # Only iterate keys/dials if there is animated content to update
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
            has_pending = bool(self.tasks or self.image_tasks or self.touchscreen_task or self.touchscreen_region_tasks)
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

            if self._stop_requested:
                break

        self.running = False

    def _needs_key_ticks(self) -> bool:
        # Check once per second whether any key/dial has animated content
        # (video or scrolling text) that on_media_player_tick needs to advance.
        if self.media_ticks % self.FPS != 0:
            return getattr(self, '_cached_needs_ticks', False)
        needs = False
        for key in self.deck_controller.inputs.get(Input.Key, []):
            state = key.get_active_state()
            if state.key_video is not None or state.label_manager.get_has_scroll_labels():
                needs = True
                break
        if not needs:
            for dial in self.deck_controller.inputs.get(Input.Dial, []):
                state = dial.get_active_state()
                if state.video is not None or state.label_manager.get_has_scroll_labels():
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
        self._stop_requested = True
        self._wake_event.set()
        while self.running:
            time.sleep(0.1)

    def boost_input_priority(self, identifier: InputIdentifier, duration: float = TASK_PRIORITY_BOOST_WINDOW):
        self.priority_boosts[identifier] = time.monotonic() + duration

    def _effective_priority(self, identifier: InputIdentifier | None, priority: int) -> int:
        if identifier is None:
            return priority

        deadline = self.priority_boosts.get(identifier)
        if deadline is None:
            return priority

        if time.monotonic() > deadline:
            self.priority_boosts.pop(identifier, None)
            return priority

        return max(priority, TASK_PRIORITY_HIGH)

    def add_task(self, method: callable, *args, task_label: str = "", **kwargs):
        self.tasks.append(MediaPlayerTask(
            deck_controller=self.deck_controller,
            page=self.deck_controller.active_page,
            _callable=method,
            args=args,
            kwargs=kwargs,
            task_label=task_label,
            created_at=time.time(),
        ))
        self._wake_event.set()

    def _discard_touchscreen_task(self, task: MediaPlayerSetTouchscreenImageTask | None):
        if task is not None:
            task.close()

    def _discard_touchscreen_regions(self):
        for task in self.touchscreen_region_tasks.values():
            task.close()
        self.touchscreen_region_tasks.clear()

    def add_touchscreen_task(
        self,
        image: Image.Image,
        x_pos: int = 0,
        y_pos: int = 0,
        width: int = None,
        height: int = None,
        priority: int = TASK_PRIORITY_NORMAL,
        identifier: InputIdentifier = None,
    ):
        if width is None or height is None:
            width, height = image.size

        priority = self._effective_priority(identifier, priority)

        task = MediaPlayerSetTouchscreenImageTask(
            deck_controller=self.deck_controller,
            page=self.deck_controller.active_page,
            image=image,
            x_pos=x_pos,
            y_pos=y_pos,
            width=width,
            height=height,
            priority=priority,
        )
        self._wake_event.set()

        touchscreen_size = self.deck_controller.get_touchscreen_image_size()
        is_full_screen = (
            x_pos == 0 and y_pos == 0 and
            width == touchscreen_size[0] and height == touchscreen_size[1]
        )
        self._wake_event.set()

        if is_full_screen:
            self._discard_touchscreen_task(self.touchscreen_task)
            self.touchscreen_task = task
            self._discard_touchscreen_regions()
            return

        region = (x_pos, y_pos, width, height)
        existing = self.touchscreen_region_tasks.get(region)
        if existing is not None:
            if existing.image_hash == task.image_hash and existing.priority >= task.priority:
                task.close()
                return
            existing.close()
        self.touchscreen_region_tasks[region] = task

    def add_image_task(
        self,
        key_index: int,
        native_image: bytes,
        priority: int = TASK_PRIORITY_NORMAL,
        identifier: InputIdentifier = None,
    ):
        priority = self._effective_priority(identifier, priority)
        image_hash = _hash_payload(native_image)

        existing = self.image_tasks.get(key_index)
        if existing is not None and existing.image_hash == image_hash and existing.priority >= priority:
            return
        if existing is not None:
            existing.close()

        self.image_tasks[key_index] = MediaPlayerSetImageTask(
            deck_controller=self.deck_controller,
            page=self.deck_controller.active_page,
            key_index=key_index,
            native_image=native_image,
            priority=priority,
            image_hash=image_hash,
        )
        self._wake_event.set()

    def _merge_touchscreen_tasks(
        self,
        tasks: list[MediaPlayerSetTouchscreenImageTask]
    ) -> list[MediaPlayerSetTouchscreenImageTask]:
        merged: list[MediaPlayerSetTouchscreenImageTask] = []
        for task in sorted(tasks, key=lambda t: (t.y_pos, t.x_pos)):
            if not merged:
                merged.append(task)
                continue

            previous = merged[-1]
            if previous.can_merge_with(task):
                merged[-1] = previous.merge_with(task)
            else:
                merged.append(task)

        return merged

    def perform_media_player_tasks(self):
        for task in self.tasks.copy():
            if task.page is self.deck_controller.active_page:
                task_start = time.time()
                task.run()
                task_runtime = (time.time() - task_start) * 1000
                queue_wait = (task_start - task.created_at) * 1000 if task.created_at else 0
                if task_runtime > 60:
                    log.debug(f"[media-task] deck={self.deck_controller.safe_serial_number()} label={task.task_label or task._callable.__name__} queue_wait_ms={queue_wait:.1f} run_ms={task_runtime:.1f}")

            try:
                self.tasks.remove(task)
            except ValueError:
                pass

        key_tasks: list[MediaPlayerSetImageTask] = []
        for key in list(self.image_tasks.keys()):
            try:
                task = self.image_tasks.pop(key)
            except KeyError:
                continue

            if task.page is not self.deck_controller.active_page:
                task.close()
                continue

            if self.last_key_image_hashes.get(key) == task.image_hash:
                task.close()
                continue

            key_tasks.append(task)

        full_touchscreen_task = self.touchscreen_task
        self.touchscreen_task = None

        region_tasks = list(self.touchscreen_region_tasks.values())
        self.touchscreen_region_tasks = {}

        if full_touchscreen_task is not None and full_touchscreen_task.page is not self.deck_controller.active_page:
            full_touchscreen_task.close()
            full_touchscreen_task = None

        valid_region_tasks: list[MediaPlayerSetTouchscreenImageTask] = []
        for task in region_tasks:
            if task.page is not self.deck_controller.active_page:
                task.close()
                continue
            valid_region_tasks.append(task)

        valid_region_tasks = self._merge_touchscreen_tasks(valid_region_tasks)
        deduped_region_tasks: list[MediaPlayerSetTouchscreenImageTask] = []
        for task in valid_region_tasks:
            if self.last_touchscreen_hashes.get(task.region_key()) == task.image_hash:
                task.close()
                continue
            deduped_region_tasks.append(task)
        valid_region_tasks = deduped_region_tasks

        if full_touchscreen_task is not None and self.last_touchscreen_hashes.get(full_touchscreen_task.region_key()) == full_touchscreen_task.image_hash:
            full_touchscreen_task.close()
            full_touchscreen_task = None

        has_hardware_updates = any([key_tasks, full_touchscreen_task, valid_region_tasks])
        if has_hardware_updates:
            with self.deck_controller.deck:
                for task in sorted(key_tasks, key=lambda t: (-t.priority, t.key_index)):
                    task.run()
                    self.last_key_image_hashes[task.key_index] = task.image_hash

                if full_touchscreen_task is not None:
                    full_touchscreen_task.run()
                    self.last_touchscreen_hashes.clear()
                    self.last_touchscreen_hashes[full_touchscreen_task.region_key()] = full_touchscreen_task.image_hash

                for task in sorted(valid_region_tasks, key=lambda t: (-t.priority, t.y_pos, t.x_pos)):
                    task.run()
                    self.last_touchscreen_hashes[task.region_key()] = task.image_hash

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


@lru_cache(maxsize=64)
def _decode_page_media_cached(path: str, mtime: float, is_svg_media: bool) -> Image.Image:
    # Keyed on (path, mtime) so re-visiting a page doesn't re-decode/re-rasterize
    # media from disk every time. GIFs/videos aren't cached here since they animate.
    if is_svg_media:
        return svg_to_pil(path, 192)
    with Image.open(path) as im:
        return im.copy()


def get_page_media_image(path: str, is_svg_media: bool) -> Image.Image:
    # Returns a fresh copy each time, since callers may mutate/close it.
    try:
        mtime = os.path.getmtime(path)
    except OSError:
        if is_svg_media:
            return svg_to_pil(path, 192)
        with Image.open(path) as im:
            return im.copy()
    return _decode_page_media_cached(path, mtime, is_svg_media).copy()


class DeckController:
    def __init__(self, deck_manager: "DeckManager", deck: StreamDeck.StreamDeck):
        self.deck_manager: DeckManager = deck_manager
        # Open the deck - why store it as self.deck? So that self.get_alive() returns True in get_deck_settings
        self.deck = deck
        try:
            self.deck.open(self.deck_manager.beta_resume_mode)
            rotation = self.get_deck_settings().get("rotation", 0)
        except Exception as e:
            log.error(f"Failed to open deck or read its settings, maybe it's already connected to another instance? Skipping... Error: {e}")
            # open() may have already started a reader thread even though the
            # settings read right after it failed - leaving it running would
            # leak an open, untracked device (see issue #604)
            try:
                self.stop_reader()
                if self.deck.is_open():
                    self.deck.close()
            except Exception as close_error:
                log.error(f"Failed to close deck after failed open. Error: {close_error}")
            del self
            return

        self.deck: RotatedDeck = RotatedDeck(deck, rotation)

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
        self.update_key_spacing()

        # Tasks
        self.media_player_tasks: Queue[MediaPlayerTask] = Queue()

        self.ui_image_changes_while_hidden: dict = {}

        self._last_gc_time: float = 0.0

        self.active_page: Page = None

        self.inputs = {}
        for i in Input.All:
            self.inputs[i] = []
        self.init_inputs()

        self.background = Background(self)
        self.background_rotation = BackgroundRotation(self)

        self.deck.set_key_callback(self.key_event_callback)
        self.deck.set_dial_callback(self.dial_event_callback)
        self.deck.set_touchscreen_callback(self.touchscreen_event_callback)

        # Start media player thread
        self.media_player = MediaPlayerThread(deck_controller=self)
        self.media_player.start()
        self.input_load_executor = ThreadPoolExecutor(max_workers=max(2, min(8, os.cpu_count() or 4)))

        self.keep_actions_ticking = True
        self.TICK_DELAY = 1
        self.tick_thread = Thread(target=self.tick_actions, name="tick_actions")
        self.tick_thread.start()

        self.page_auto_loaded: bool = False
        self.last_manual_loaded_page_path: str = None
        self._last_background_signature: tuple | None = None
        self._last_screensaver_signature: tuple | None = None

        deck_settings = self.get_deck_settings()

        # None so the first set_brightness() call always writes to the device
        self.brightness = None
        brightness = deck_settings.get("brightness", {}).get("value", 75)
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

    def update_key_spacing(self):
        """
        Bezel size between the keys, used to crop deck sized backgrounds.

        Note that self.deck is a RotatedDeck, so the device itself has to be unwrapped
        for the isinstance checks.
        """
        device = getattr(self.deck, "deck", self.deck)

        # Only the Plus needs this - the Plus XL is spaced like the other decks
        is_plus = isinstance(device, StreamDeckPlus) or (
            isinstance(device, FakeDeck) and issubclass(device.emulated_class, StreamDeckPlus)
        )

        if not is_plus:
            self.key_spacing = (36, 36)
            return

        log.debug("Deck recognized as StreamDeckPlus")
        # The gap is wider between columns - which becomes the gap between rows
        # once the deck is turned onto its side
        if self.deck.get_rotation() % 180 == 0:
            self.key_spacing = (52, 36)
        else:
            self.key_spacing = (36, 52)

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

    def safe_serial_number(self) -> str:
        try:
            return self.serial_number()
        except Exception:
            return "unknown"
    
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
        if self.active_page is None:
            return
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
        # key is already a logical index (RotatedDeck.set_key_callback maps it),
        # so it has to be resolved against the rotation aware layout of
        # self.deck - the very same math Available_Identifiers uses.
        coords = ControllerKey.Index_To_Coords(self.deck, key)
        ident = Input.Key(f"{coords[0]}x{coords[1]}")
        self.event_callback(ident,*args, **kwargs)

    def dial_event_callback(self, deck, dial, *args, **kwargs):
        ident = Input.Dial(str(dial))
        self.event_callback(ident, *args, **kwargs)

    def touchscreen_event_callback(self, deck, event_type, value, *args, **kwargs):
        # The device reports physical positions - everything above works in logical ones
        value = self.deck.touch_value_to_logical(value)
        ident = Input.Touchscreen("sd-plus")
        self.event_callback(ident, event_type, value, *args, **kwargs)

    def trigger_action(self, coords: str, event: str) -> tuple[bool, str]:
        """
        Simulate a physical key press/release for CLI-driven automation (--action).
        Reuses ControllerKey.event_callback so the same down/hold/up sequence and
        plugin hooks fire as for a real press.
        """
        try:
            x, y = map(int, coords.split(','))
        except (ValueError, AttributeError):
            return False, f"Invalid coordinate format '{coords}'. Expected format: 'x,y' (e.g., '0,0')"

        rows, cols = self.deck.key_layout()
        if x < 0 or x >= cols or y < 0 or y >= rows:
            return False, f"Coordinates ({x},{y}) are out of bounds for this device. Valid range: x=0-{cols-1}, y=0-{rows-1}"

        identifier = Input.Key(f"{x}x{y}")
        c_input = self.get_input(identifier)
        if c_input is None:
            return False, f"Could not find input at coordinates ({x},{y})"

        if event == "press":
            release_delay = 0.05
        elif event == "long-press":
            release_delay = self.hold_time + 0.1
        else:
            return False, f"Unknown action event '{event}'. Supported events: press, long-press"

        def _simulate_press():
            c_input.event_callback(True)
            time.sleep(release_delay)
            c_input.event_callback(False)

        threading.Thread(target=_simulate_press, name="cli-trigger-action", daemon=True).start()
        return True, f"Triggered '{event}' at ({x},{y}) on device {self.serial_number()}"

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
        """Size of the touchscreen as we render it, i.e. rotation applied."""
        if not self.get_alive(): return
        size = self.deck.logical_touchscreen_size()
        if size is None:
            # Deck without a touchscreen, or one that does not report its size -
            # fall back to the size of the Plus
            size = (100, 800) if self.deck.get_rotation() in [90, 270] else (800, 100)
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

        # Handle action trigger requests
        if self.serial_number() in gl.api_action_requests:
            action_request = gl.api_action_requests[self.serial_number()]
            event = action_request["event"]
            page_name = action_request["page_name"]
            coords = action_request["coords"]

            requested_page_path = gl.page_manager.find_matching_page_path(page_name)

            if requested_page_path is None:
                available_pages = [os.path.splitext(os.path.basename(p))[0] for p in gl.page_manager.get_pages()]
                log.error(f"Action trigger failed: Page '{page_name}' not found for device {self.serial_number()}. Available pages: {', '.join(available_pages)}")
            else:
                if os.path.abspath(requested_page_path) != os.path.abspath(self.active_page.json_path):
                    requested_page = gl.page_manager.get_page(requested_page_path, self)
                    self.load_page(requested_page)

                success, message = self.trigger_action(coords, event)
                if success:
                    log.info(message)
                else:
                    log.error(f"Action trigger failed: {message}")

            del gl.api_action_requests[self.serial_number()]

    @log.catch
    def load_background(self, page: Page, update: bool = True, force_reload: bool = False):
        start = time.time()
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

        source = config.get("source", "file")
        folder_path = config.get("folder-path")
        rotation_interval = int(config.get("rotation-interval", 5))

        background_signature = (
            bool(config.get("media-path")),
            config.get("media-path"),
            bool(config.get("loop", False)),
            int(config.get("fps", 30)),
            source,
            folder_path,
            rotation_interval,
        )
        if not force_reload and background_signature == self._last_background_signature:
            log.debug(f"[page-switch-phase] deck={self.safe_serial_number()} phase=background skip=unchanged")
            return
        self._last_background_signature = background_signature

        if source == "folder" and folder_path:
            self.background_rotation.start(
                folder_path=folder_path,
                interval=rotation_interval,
                loop=config.get("loop", False),
                fps=config.get("fps", 30),
                update=update,
            )
        else:
            self.background_rotation.stop()
            self.background.set_from_path(
                path=config.get("media-path"),
                update=update,
                loop=config.get("loop", False),
                fps=config.get("fps", 30),
            )
        log.debug(f"[page-switch-phase] deck={self.safe_serial_number()} phase=background ms={(time.time() - start) * 1000:.1f}")

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
        start = time.time()
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

        screensaver_signature = (
            bool(config.get("enable", False)),
            config.get("media-path"),
            int(config.get("time-delay", 5)),
            bool(config.get("loop", False)),
            int(config.get("fps", 30)),
            int(config.get("brightness", 30)),
            config.get("source", "file"),
            config.get("folder-path"),
            int(config.get("rotation-interval", 5)),
        )
        if screensaver_signature == self._last_screensaver_signature:
            log.debug(f"[page-switch-phase] deck={self.safe_serial_number()} phase=screensaver skip=unchanged")
            return
        self._last_screensaver_signature = screensaver_signature

        # Before the media path, so a path change already applies the new source
        self.screen_saver.set_source(config.get("source", "file"))
        self.screen_saver.set_folder_path(config.get("folder-path"))
        self.screen_saver.set_rotation_interval(config.get("rotation-interval", 5))

        self.screen_saver.set_media_path(config.get("media-path"))
        self.screen_saver.set_enable(config.get("enable", False))
        self.screen_saver.set_time(config.get("time-delay", 5))
        self.screen_saver.set_loop(config.get("loop", False))
        self.screen_saver.set_fps(config.get("fps", 30))
        self.screen_saver.set_brightness(config.get("brightness", 30))
        log.debug(f"[page-switch-phase] deck={self.safe_serial_number()} phase=screensaver ms={(time.time() - start) * 1000:.1f}")

    @log.catch
    def load_all_inputs(self, page: Page, update: bool = True):
        start = time.time()
        controller_inputs = [controller_input for t in self.inputs for controller_input in self.inputs[t]]

        # Avoid dispatch overhead for small decks/pages.
        if len(controller_inputs) <= 16:
            for controller_input in controller_inputs:
                self.load_input(controller_input, page, update)
        else:
            futures = [self.input_load_executor.submit(self.load_input, controller_input, page, update) for controller_input in controller_inputs]
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
    def load_page(self, page: Page, load_brightness: bool = True, load_screensaver: bool = True, load_background: bool = True, load_inputs: bool = True, allow_reload: bool = True, force_background_reload: bool = False):
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

        log.info(f"Loading page {page.get_name()} on deck {self.safe_serial_number()}")

        # Stop queued tasks. Also waits out any in-flight media tick, so we don't
        # need a second wait here anymore.
        self.clear_media_player_tasks()

        # Update ui
        GLib.idle_add(self.update_ui_on_page_change) #TODO: Use new signal manager instead

        if load_background:
            # self.load_background(page, update=False)
            self.media_player.add_task(
                self.load_background,
                page,
                update=False,
                force_reload=force_background_reload,
                task_label=f"load_background:{page.get_name()}",
            )
        if load_brightness:
            t_brightness = time.time()
            self.load_brightness(page)
            brightness_ms = (time.time() - t_brightness) * 1000
        else:
            brightness_ms = 0.0
        if load_screensaver:
            t_screensaver = time.time()
            self.load_screensaver(page)
            screensaver_ms = (time.time() - t_screensaver) * 1000
        else:
            screensaver_ms = 0.0
        if load_inputs:
            self.media_player.add_task(self.load_all_inputs, page, update=False, task_label=f"load_all_inputs:{page.get_name()}")

        t_initialize_actions = time.time()
        self.active_page.initialize_actions()
        initialize_actions_ms = (time.time() - t_initialize_actions) * 1000

        # Load page onto deck
        self.media_player.add_task(self.update_all_inputs, task_label=f"update_all_inputs:{page.get_name()}")

        # Notify plugin actions
        gl.signal_manager.trigger_signal(Signals.ChangePage, self, old_path, self.active_page.json_path)

        # Notify DBus API of the page change
        notify_active_page_changed(self.serial_number(), page.get_name())

        total_ms = (time.time() - start) * 1000
        log.info(f"Loaded page {page.get_name()} on deck {self.safe_serial_number()}")
        log.info(f"[page-switch] deck={self.safe_serial_number()} page={page.get_name()} total_ms={total_ms:.1f}")
        log.debug(f"[page-switch-phase] deck={self.safe_serial_number()} page={page.get_name()} brightness_ms={brightness_ms:.1f} screensaver_ms={screensaver_ms:.1f} initialize_actions_ms={initialize_actions_ms:.1f}")
        self.maybe_collect_garbage()

    # Minimum seconds between post-load garbage collections, so rapid page
    # switching doesn't trigger a full GC pause on every single switch.
    GC_MIN_INTERVAL = 10.0

    def maybe_collect_garbage(self):
        now = time.time()
        if now - self._last_gc_time < self.GC_MIN_INTERVAL:
            return
        self._last_gc_time = now
        gc.collect()

    def reload_page(self):
        self.load_page(
            page=self.active_page,
            allow_reload=True
        )

    def set_brightness(self, value):
        value = min(100, max(0, value))
        if not self.get_alive(): return
        if value == self.brightness:
            # Skip the write if brightness didn't change - the device can stall
            # noticeably on this while it's busy with an image-write burst.
            return
        self.deck.set_brightness(int(value))
        self.brightness = value

    def set_rotation(self, value):
        if value == self.deck.get_rotation():
            return

        if not self.get_alive():
            # Nothing to re-render - remember it for whenever the deck comes back
            self.deck.set_rotation(value)
            return

        page = self.active_page

        # Keep the media player off the inputs while they are being swapped out
        self.media_player.pause = True
        try:
            self._apply_rotation(value)
        finally:
            self.media_player.pause = False

        self.load_page(page, allow_reload=True)

    def _apply_rotation(self, value):
        # Everything below is layout dependent, so tear it down before the layout changes
        self.clear_media_player_tasks()
        self.close_image_ressources()

        self.deck.set_rotation(value)

        # These derive from the rotation aware layout, so they have to be re-computed
        DeckController.get_key_image_size.cache_clear()
        DeckController.get_touchscreen_image_size.cache_clear()
        self.update_key_spacing()

        # The key identifiers and indices are derived from the (rotation aware) key
        # layout, so the inputs have to be rebuilt for the new one. As a welcome side
        # effect the fresh ControllerKeys carry no stale _last_img_hash, which would
        # otherwise make update() skip re-rendering (the hash is of the unrotated image,
        # which does not change when only the rotation does).
        self.inputs = {}
        self.init_inputs()

        # Nothing that is currently on the device can be trusted anymore: the render
        # caches are keyed by logical index/region, but the logical -> physical mapping
        # just changed underneath them.
        self.invalidate_render_caches()
        self.ui_image_changes_while_hidden.clear()
        self.clear()

        self.rebuild_ui_for_rotation()

    def invalidate_render_caches(self):
        """
        Forget everything we believe is currently displayed on the device.

        Both the per input image hash and the media player hashes exist to skip
        redundant writes to the hardware. They have to be dropped whenever the device
        content changed behind our back (reconnect) or the logical -> physical mapping
        changed (rotation), because otherwise an unchanged image is never re-sent.
        """
        for t in self.inputs:
            for i in self.inputs[t]:
                i._last_img_hash = None

        self.media_player.last_key_image_hashes.clear()
        self.media_player.last_touchscreen_hashes.clear()

    def rebuild_ui_for_rotation(self):
        """Re-create the key grid, screen bar and dials for the new layout."""
        self.own_key_grid = None

        deck_stack_child = self.get_own_deck_stack_child()
        if deck_stack_child is None:
            # Ui not built yet - it will be created with the new layout anyway
            return

        deck_stack_child.page_settings.deck_config.rebuild_for_rotation()


    def tick_actions(self) -> None:
        time.sleep(self.TICK_DELAY)
        while self.keep_actions_ticking:
            start = time.time()
            if self.active_page is None:
                time.sleep(0.1)
                continue
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
            # Uniform black, so build it in physical orientation and skip the mapping
            touchscreen_size = self.deck.physical_touchscreen_size() or (800, 100)
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

        # Wake it up instead of waiting for its idle cycle to come around on its own
        self.media_player._wake_event.set()

        # Wait for the tick to be over so no stale task is still running, bounded
        # so this can't hang if the media thread is ever stalled
        deadline = time.time() + 0.5
        while self.media_player.media_ticks <= ticks and time.time() < deadline:
            time.sleep(1/60)

    def clear_media_player_tasks_via_task(self):
        self.media_player_tasks.append(MediaPlayerTask(
            deck_controller=self,
            page=self.active_page,
            _callable=self.clear_media_player_tasks,
            args=(),
            kwargs={},
        ))

    def stop_reader(self, timeout: float = 2) -> None:
        """
        Stop the reader thread of the StreamDeck library and wait for it to exit.

        This has to happen before the device is closed. A reader that is still
        running reads a closed handle, ends up in its TransportError handler and -
        because the deck is still plugged in - reopens the device as if we had just
        resumed from suspend. The process then exits with an open HID device, which
        makes libusb abort in usbi_mutex_destroy() (see issue #631).

        Note that self.deck is a RotatedDeck, so the device itself has to be
        unwrapped - the wrapper does not forward attribute assignments.
        """
        device = getattr(self.deck, "deck", self.deck)
        if not hasattr(device, "read_thread"):
            # Fake and remote decks have no reader thread
            return

        # Don't let the reader bring the device back up while we are closing it
        device.reconnect_after_suspend = False
        device.run_read_thread = False

        read_thread = device.read_thread
        if read_thread is None or read_thread is threading.current_thread():
            return

        read_thread.join(timeout=timeout)
        if read_thread.is_alive():
            # device.id() is the cached device path - unlike the serial number it
            # does not talk to a deck we are about to close
            log.error(f"Reader thread of deck {device.id()} did not exit in time")

    def delete(self):
        if hasattr(self, "active_page"):
            if self.active_page is not None:
                self.active_page.action_objects = {}

        if hasattr(self, "media_player"):
            self.media_player.stop()
        if hasattr(self, "input_load_executor"):
            self.input_load_executor.shutdown(wait=False, cancel_futures=True)
        if hasattr(self, "background_rotation"):
            self.background_rotation.stop()
        if hasattr(self, "background"):
            if getattr(self.background, "video", None) is not None:
                self.background.video.close()
                self.background.video = None
            if getattr(self.background, "standby_video", None) is not None:
                self.background.standby_video.close()
                self.background.standby_video = None

        self.keep_actions_ticking = False
        self.stop_reader()

    def get_alive(self) -> bool:
        try:
            return self.deck.is_open()
        except Exception as e:
            log.debug(f"Cougth dead deck error. Error: {e}")
            return False

class BackgroundRotation:
    """
    Cycles the background through the media files of a folder.

    The switch itself is queued as a media player task so it happens on the same
    thread as every other background change - the timer thread must not touch the
    background on its own.
    """
    def __init__(self, deck_controller: DeckController):
        self.deck_controller = deck_controller

        self.folder_path: str = None
        self.interval: int = 5 # In minutes
        self.loop: bool = False
        self.fps: int = 30

        self.index: int = 0
        self.timer: Timer = None
        self.lock = threading.Lock()

    def start(self, folder_path: str, interval: int, loop: bool = False, fps: int = 30, update: bool = True) -> None:
        with self.lock:
            if folder_path != self.folder_path:
                self.index = 0
            self.folder_path = folder_path
            self.interval = max(1, int(interval))
            self.loop = loop
            self.fps = fps

        self.show_current(update=update)
        self.restart_timer()

    def stop(self) -> None:
        with self.lock:
            self.folder_path = None
            if self.timer is not None:
                self.timer.cancel()
                self.timer = None

    def get_current_path(self) -> str:
        paths = get_folder_media_paths(self.folder_path)
        if len(paths) == 0:
            return None
        return paths[self.index % len(paths)]

    def show_current(self, update: bool = True) -> None:
        self.deck_controller.background.set_from_path(
            path=self.get_current_path(),
            update=update,
            loop=self.loop,
            fps=self.fps,
        )

    def restart_timer(self) -> None:
        with self.lock:
            if self.timer is not None:
                self.timer.cancel()
                self.timer = None
            if self.folder_path is None:
                return

            self.timer = Timer(self.interval * 60, self.on_timer)
            self.timer.daemon = True
            self.timer.start()

    def on_timer(self) -> None:
        self.index += 1
        # The screen saver owns the background while it is showing. Skipping keeps it
        # from being painted over - hide() reloads the page and picks the new index up.
        if not self.deck_controller.screen_saver.showing:
            self.deck_controller.media_player.add_task(self.show_current, task_label="rotate_background")
        self.restart_timer()


class Background:
    def __init__(self, deck_controller: DeckController):
        self.deck_controller = deck_controller

        self.image = None
        self.video = None
        self.standby_video: "BackgroundVideo | None" = None

        self.tiles: list[Image.Image] = [None] * deck_controller.deck.key_count()

    def _park_video(self, video: "BackgroundVideo | None") -> None:
        if video is None:
            return
        if self.standby_video is not None and self.standby_video is not video:
            self.standby_video.close()
        self.standby_video = video

    def set_image(self, image: "BackgroundImage", update: bool = True) -> None:
        if self.image is not None:
            self.image.close()
        self.image = image
        if self.video is not None:
            self._park_video(self.video)
        self.video = None
        gc.collect()

        self.update_tiles()
        if update:
            self.deck_controller.update_all_inputs()

    def set_video(self, video: "BackgroundVideo", update: bool = True) -> None:
        if self.image is not None:
            self.image.close()
        if self.video is not None and self.video is not video:
            self._park_video(self.video)
        self.image = None
        self.video = video
        if self.standby_video is video:
            self.standby_video = None
        gc.collect()

        self.update_tiles()
        if update:
            self.deck_controller.update_all_inputs()

    def set_from_path(self, path: str, fps: int = 30, loop: bool = True, update: bool = True, allow_keep: bool = True) -> None:
        if path == "":
            path = None
        if path is None:
            self.image = None
            # self.video = None
            self.set_video(None, update=False)
            self.update_tiles()
            if update:
                self.deck_controller.update_all_inputs()
        elif is_video(path):
            if allow_keep:
                if self.video is not None and self.video.video_path == path:
                    self.video.page = self.deck_controller.active_page
                    self.video.fps = fps
                    self.video.loop = loop
                    return
                if self.video is None and self.standby_video is not None and self.standby_video.video_path == path:
                    self.standby_video.page = self.deck_controller.active_page
                    self.standby_video.fps = fps
                    self.standby_video.loop = loop
                    self.set_video(self.standby_video, update=update)
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

    def close(self) -> None:
        if self.image is not None:
            self.image.close()
            self.image = None

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

        # Convert to RGBA first to preserve transparency, then resize
        img_rgba = self.image.convert("RGBA")
        return ImageOps.fit(img_rgba, full_deck_image_size, Image.LANCZOS)
    
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

        # Return the segment directly, converting to RGBA to preserve transparency
        return segment.convert("RGBA")
    
    def get_tiles(self) -> list[Image.Image]:
        full_deck_sized_image = self.create_full_deck_sized_image()

        tiles: list[Image.Image] = []
        for key in range(self.deck_controller.deck.key_count()):
            key_image = self.crop_key_image_from_deck_sized_image(full_deck_sized_image, key)
            tiles.append(key_image)
        full_deck_sized_image.close()

        return tiles

    def close(self) -> None:
        if self.image is None:
            return
        self.image.close()
        self.image = None

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
            if self.loop:
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

        # Return the cropped segment directly, preserving alpha (matches
        # BackgroundImage.crop_key_image_from_deck_sized_image above) instead
        # of pasting onto an opaque RGB key image, which silently dropped
        # transparency for GIF backgrounds.
        return segment.convert("RGBA")

class KeyGIF(SingleKeyAsset):
    def __init__(self, controller_key: "ControllerKey", gif_path: str, fps: int = 30, loop: bool = True):
        super().__init__(controller_key)
        self.gif_path = gif_path
        self.fps = fps
        self.loop = loop

        self.active_frame: int = -1

        self.gif = Image.open(self.gif_path)
        self.frames = []
        self.frame_delays = []
        
        # Extract frames and their delays
        for frame in ImageSequence.Iterator(self.gif):
            self.frames.append(frame.convert("RGBA"))
            # Get frame delay from GIF metadata (in milliseconds)
            # Default to 100ms (10fps) if no delay specified
            delay = self.gif.info.get('duration', 100)
            # Some GIFs use delay in centiseconds, convert to milliseconds
            if delay < 50:
                delay *= 10
            self.frame_delays.append(delay)

    def get_next_frame(self) -> Image.Image:
        self.active_frame += 1

        if self.active_frame >= len(self.frames):
            if self.loop:
                self.active_frame = 0
            else:
                self.active_frame = len(self.frames) - 1

        return self.frames[self.active_frame]
    
    def get_frame_delay(self) -> float:
        """Get delay for current frame in seconds"""
        if self.active_frame < 0 or self.active_frame >= len(self.frame_delays):
            return 1.0 / self.fps  # Fallback to fps-based timing
        return self.frame_delays[self.active_frame] / 1000.0  # Convert ms to seconds
    
    def get_raw_image(self) -> Image.Image:
        return self.get_next_frame()
    
    def close(self) -> None:
        self.gif = None
        self.frames = None
        self.frame_delays = None
        del self.gif
        del self.frames
        del self.frame_delays

class LabelManager:
    def __init__(self, controller_input: "ControllerInput"):
        self.controller_input = controller_input
        
        self.page_labels = {}
        self.action_labels = {}
        self.scroll_wait = 25
        self._has_scroll_labels_cache: bool = None

        self.init_labels()
        self.frames: dict[str, dict[str, int]] = {
            "top": {
                "position": 0,
                "wait": self.scroll_wait
            },
            "center": {
                "position": 0,
                "wait": self.scroll_wait
            },
            "bottom": {
                "position": 0,
                "wait": self.scroll_wait
            },
        }

    def init_labels(self):
        for position in ["top", "center", "bottom"]:
            self.page_labels[position] = KeyLabel(self.controller_input)
            self.action_labels[position] = KeyLabel(self.controller_input)

    def clear_labels(self):
        self.init_labels()
        self._has_scroll_labels_cache = None

    def set_page_label(self, position: str, label: "KeyLabel", update: bool = True):
        if label is None:
            label = self.page_labels[position]
            label.clear_values()
        else:
            self.page_labels[position] = label

        self._has_scroll_labels_cache = None
        if update:
            self.update_label(position)

    @staticmethod
    def _label_equals(a: "KeyLabel", b: "KeyLabel") -> bool:
        return (a.text == b.text and a.font_size == b.font_size
                and a.font_name == b.font_name and a.color == b.color
                and a.font_weight == b.font_weight and a.style == b.style
                and a.outline_width == b.outline_width
                and a.outline_color == b.outline_color
                and a.alignment == b.alignment)

    def set_action_label(self, position: str, label: "KeyLabel", update: bool = True):
        if label is None:
            label = self.action_labels[position]
            label.clear_values()
        else:
            old = self.action_labels.get(position)
            if old is not None and self._label_equals(old, label):
                return
            self.action_labels[position] = label

        self._has_scroll_labels_cache = None
        GLib.idle_add(self.update_label_editor)
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
                "alignment": False,
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
            "alignment": self.page_labels[position].alignment is not None,
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
            if use_page_label_properties["alignment"]:
                label.alignment = page_label.alignment

        injected = self.inject_defaults(label)
        return self.fix_invalid(injected)
    
    def get_composed_labels(self) -> dict[str, "KeyLabel"]:
        composed_labels = {}
        for position in ["top", "center", "bottom"]:
            composed_labels[position] = self.get_composed_label(position)
        return composed_labels

    
    def inject_defaults(self, label: "KeyLabel"):
        if label.text is None:
            label.text = ""
        if label.color is None:
            label.color = gl.settings_manager.font_defaults.get("font-color") or (255, 255, 255, 255)
        if label.font_name is None:
            label.font_name = gl.settings_manager.font_defaults.get("font-family") or gl.fallback_font
        if label.font_size is None:
            label.font_size = round(gl.settings_manager.font_defaults.get("font-size") or 15)
        if label.font_weight is None:
            label.font_weight = round(gl.settings_manager.font_defaults.get("font-weight") or 400)
        if label.style is None:
            label.style = gl.settings_manager.font_defaults.get("font-style") or "normal"
        if label.outline_width is None:
            label.outline_width = round(gl.settings_manager.font_defaults.get("outline-width") or 2)
        if label.outline_color is None:
            label.outline_color = gl.settings_manager.font_defaults.get("outline-color") or (0, 0, 0, 255)
        if label.alignment is None:
            label.alignment = gl.settings_manager.font_defaults.get("alignment") or "center"

        return label
    
    def fix_invalid(self, label: "KeyLabel"):
        if not isinstance(label.text, str):
            label.text = str(label.text)

        return label

    def update_label(self, position: str):
        self.controller_input.update()

    def get_available_width(self) -> int:
        return self.controller_input.get_image_size()[0]

    def get_has_scroll_labels(self) -> bool:
        if self._has_scroll_labels_cache is not None:
            return self._has_scroll_labels_cache

        labels = self.get_composed_labels()
        for label in labels:
            if labels[label].text is not None and labels[label].text != "":
                _, _, w, _ = labels[label].get_font().getbbox(labels[label].text)
                if w > self.get_available_width():
                    self._has_scroll_labels_cache = True
                    return True
        self._has_scroll_labels_cache = False
        return False

    def add_labels_to_image(self, image: Image.Image) -> Image.Image:
        # image = image.rotate(self.deck.get_rotation()*-1)
        draw = ImageDraw.Draw(image)

        labels = self.get_composed_labels()
        for label in labels:
            text = labels[label].text
            if text in [None, ""]:
                continue

            color = tuple(labels[label].color)
            font = labels[label].get_font()
            outline_width = labels[label].outline_width
            outline_color = tuple(labels[label].outline_color)
            alignment = labels[label].alignment

            _, _, w, h = draw.textbbox((0, 0), text, font=font)

            # Calculate x position based on alignment
            padding = 3
            if alignment == "left":
                x_position = padding
                anchor_x = "l"
            elif alignment == "right":
                x_position = image.width - padding
                anchor_x = "r"
            else:  # center (default)
                x_position = image.width / 2
                anchor_x = "m"

            rolling_labels_enabled = gl.settings_manager.get_app_settings().get("general", {}).get("rolling-labels", True)
            if rolling_labels_enabled and image.width < w:
                # Need to scroll - always use center anchor for scrolling
                start = image.width / 2 - (image.width - w) / 2 + 10
                stop = image.width / 2 + (image.width - w) / 2 - 10

                x_position = start - self.frames[label]["position"]
                anchor_x = "m"
                if x_position < stop:
                    if self.frames[label]["wait"] == 0:
                        x_position = start
                        self.frames[label]["position"] = 0
                        self.frames[label]["wait"] = self.scroll_wait
                    else:
                        self.frames[label]["wait"] -= 1
                elif self.controller_input.media_ticks % 2 == 0:
                    if self.frames[label]["wait"] == 0:
                        if x_position == stop:
                            self.frames[label]["wait"] = self.scroll_wait

                        self.frames[label]["position"] += 1
                    else:
                        self.frames[label]["wait"] -= 1


            if label == "top":
                position = (x_position, h/2 + 3)
            elif label == "bottom":
                position = (x_position, image.height - h/2 - 3)
            else:
                position = (x_position, (image.height - 0) / 2)

            # Use appropriate anchor based on alignment (x-anchor + "m" for vertical middle)
            anchor = anchor_x + "m"

            draw.text(position,
                      text=text, font=font, anchor=anchor, align=alignment,
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
        GLib.idle_add(self.update_layout_editor)

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
            GLib.idle_add(self.update_background_editor)

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
        self.media_ticks: int = 0

        self.is_visual: bool = True

        self.enable_states: bool = True

        # Set during page load to avoid rendering on every action update - the
        # final state gets rendered once via update_all_inputs
        self._suppress_render: bool = False

        # Renders are serialized per input. get_current_image() samples state that
        # other threads mutate while it runs - most notably press_state, which the
        # deck read thread flips in event_callback while the media player thread is
        # rendering the page that the very same press just loaded. Without this an
        # older render can finish last and overwrite the newer one in the media
        # player queue, leaving e.g. the pressed (shrunk) image of a key that has
        # already been released.
        self._render_lock = threading.RLock()

        # An update that arrived while renders were suppressed, to be replayed once
        # the suppression window closes
        self._render_pending: bool = False

        self.states: dict[int, ControllerInputState] = {
            0: self.ControllerStateClass(self, 0),
        }

        self.states[self.state].ready()

    @staticmethod
    def Available_Identifiers(deck):
        raise AttributeError

    def update(self) -> None:
        pass

    def _flush_suppressed_render(self) -> None:
        """Replay an update that got dropped while renders were suppressed."""
        if not self._render_pending:
            return
        self.update()

    def event_callback(self) -> None:
        pass

    def close_resources(self) -> None:
        for state in self.states.values():
            state.close_resources()

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
        if not recursive_hasattr(gl, "app.main_win.sidebar.active_identifier"):
            return
        if gl.app.main_win.sidebar.active_identifier != self.identifier:
            return

        gl.app.main_win.sidebar.key_editor.state_switcher.set_n_states(len(self.states))

    def get_active_state(self) -> "ControllerInputState":
        return self.states.get(self.state, self.ControllerStateClass(self, -1))

    def states_are_persistent(self) -> bool:
        """Whether the active state of this input is remembered in the page json."""
        if not self.enable_states:
            return False
        if gl.settings_manager is None:
            return False
        return gl.settings_manager.get_app_settings().get("general", {}).get("persistent-states", False)

    def get_state_to_load(self, input_dict: dict) -> int | None:
        """
        The state to activate when (re)loading this input from its page config.
        None means: keep the state the input is currently on - the behaviour from
        before persistent states existed.
        """
        if not self.states_are_persistent():
            return None

        states = input_dict.get("active_state")
        if not isinstance(states, dict):
            return None

        state = states.get(self.deck_controller.safe_serial_number())
        if not isinstance(state, int) or state not in self.states:
            # Never written yet, or it points at a state that has since been removed
            return None
        return state

    def set_state(self, state: int, update_sidebar: bool = True, allow_reload: bool = False, persist: bool = True) -> None:
        if state == self.state and not allow_reload:
            return

        if state not in self.states:
            log.error(f"Invalid state: {state}, must be one of {list(self.states.keys())}")
            return
        self.state = state

        self.get_active_state().update()

        if update_sidebar:
            self.reload_sidebar()

        # persist=False while loading a page: the page being loaded is not necessarily
        # deck_controller.active_page (see reload_similar_pages), so writing here would
        # push the loaded state into the wrong page - and overwrite the stored one
        if persist and self.states_are_persistent():
            page = self.deck_controller.active_page
            if page is not None:
                page.set_active_state(self.identifier, self.deck_controller.safe_serial_number(), state)

    def reload_sidebar(self) -> None:
        if not recursive_hasattr(gl, "app.main_win.leftArea.deck_stack"):
            return
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
         
        # GIF timing tracking
        self.last_gif_update_time: float = 0

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

    def update(self, force: bool = False, priority: int = TASK_PRIORITY_NORMAL):
        if self._suppress_render:
            # Remember it so a press/release that lands in the suppression window
            # isn't lost - see _flush_suppressed_render()
            self._render_pending = True
            return

        # Held across render and hand off, so that a render started earlier can never
        # win over one started later - see _render_lock
        with self._render_lock:
            self._render_pending = False

            image = self.get_current_image()

            # Quick hash check - skip expensive conversion if image unchanged
            img_hash = hash(image.tobytes())
            if not force and img_hash == getattr(self, '_last_img_hash', None):
                image.close()
                return
            self._last_img_hash = img_hash

            # Handle transparency properly - composite RGBA onto RGB to preserve smooth edges
            if image.mode == "RGBA":
                rgb_background = Image.new("RGB", image.size, (0, 0, 0))
                rgb_background.paste(image, (0, 0), image)
                rgb_image = rgb_background.rotate(self.deck_controller.deck.get_rotation())
            else:
                rgb_image = image.convert("RGB").rotate(self.deck_controller.deck.get_rotation())

            if self.deck_controller.is_visual():
                native_image = PILHelper.to_native_key_format(self.deck_controller.deck, rgb_image)
                rgb_image.close()
                self.deck_controller.media_player.add_image_task(
                    self.index,
                    native_image,
                    priority=priority,
                    identifier=self.identifier,
                )

            del rgb_image

        self.set_ui_key_image(image)

    def get_active_state(self) -> "ControllerKeyState":
        return super().get_active_state()

    def on_media_player_tick(self) -> None:
        self.media_ticks += 1
        current_time = time.time()

        state = self.get_active_state()
        needs_update = False
        
        # Check if we need to update based on content type
        if state.key_video is not None:
            if isinstance(state.key_video, KeyGIF):
                # Use GIF frame delay timing
                if self.last_gif_update_time == 0:
                    self.last_gif_update_time = current_time
                    needs_update = True
                else:
                    frame_delay = state.key_video.get_frame_delay()
                    if current_time - self.last_gif_update_time >= frame_delay:
                        self.last_gif_update_time = current_time
                        needs_update = True
            else:
                # For non-GIF videos, use the original FPS-based logic
                needs_update = True
        elif self.deck_controller.background.video is not None or state.label_manager.get_has_scroll_labels():
            # Other content types
            needs_update = True

        if needs_update:
            self.update(priority=TASK_PRIORITY_LOW)

    def event_callback(self, press_state):
        screensaver_was_showing = self.deck_controller.screen_saver.showing
        if press_state:
            # Only on key down this allows plugins to control screen saver without directly deactivating it
            self.deck_controller.screen_saver.on_key_change()
        if screensaver_was_showing:
            return
        
        self.deck_controller.mark_page_ready_to_clear(False)
        self.press_state = press_state
        self.deck_controller.media_player.boost_input_priority(self.identifier)

        # force, because _last_img_hash only tracks what was rendered, not what the
        # deck actually received - a render whose image task got dropped (page load,
        # clear_media_player_tasks) would otherwise make this one a no-op and leave
        # the key showing the wrong press state
        self.update(force=True)

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


        # If the background should stay full size while pressed, the image and the labels
        # are composed onto a transparent canvas instead, so that only that layer gets
        # shrunk and can be pasted back onto the untouched background
        compose_base = background
        if self.is_pressed() and not gl.settings_manager.get_app_settings().get("general", {}).get("shrink-background-on-press", True):
            compose_base = Image.new("RGBA", background.size, (0, 0, 0, 0))

        key_image: Image.Image = None
        # rotation = self.deck_controller.get_deck_settings().get("rotation", {}).get("value", 0)
        if state.key_image is not None:
            image = state.key_image.get_raw_image()
            key_image = state.layout_manager.add_image_to_background(
                image=image,
                background=compose_base
            )
        elif state.key_video is not None:
            image = state.key_video.get_raw_image()
            key_image = state.layout_manager.add_image_to_background(
                image=image,
                background=compose_base)
        else:
            key_image = compose_base

        labeled_image = state.label_manager.add_labels_to_image(key_image)

        if self.is_pressed():
            labeled_image = self.shrink_image(labeled_image)

            if compose_base is not background:
                composed_image = background.copy()
                composed_image.alpha_composite(labeled_image)
                labeled_image.close()
                labeled_image = composed_image

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

        if image.has_transparency_data:
            background.paste(image, (int((self.deck_controller.get_key_image_size()[0] - width) / 2), int((self.deck_controller.get_key_image_size()[1] - height) / 2)), image)
        else:
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

        # The state the input ends up on: the persisted one if there is one, otherwise
        # state 0 while loading and back to the live state at the end (see below)
        target_state = self.get_state_to_load(input_dict)
        self.state = 0 if target_state is None else target_state

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

            # Actions often set_media()/set_label() with update=True, which would
            # otherwise render before the page's own labels/media are even applied
            self._suppress_render = True
            try:
                state.own_actions_update() # Why not threaded? Because this would mean that some image changing calls might get executed after the next lines which blocks custom assets
            finally:
                self._suppress_render = False

            ## Load labels
            if load_labels:
                for label in state_dict.get("labels", []):
                    key_label = KeyLabel(
                        controller_input=self,
                        text=state_dict["labels"][label].get("text"),
                        font_size=state_dict["labels"][label].get("font-size"),
                        font_name=state_dict["labels"][label].get("font-family"),
                        font_weight=state_dict["labels"][label].get("font-weight"),
                        style=state_dict["labels"][label].get("style"),
                        color=state_dict["labels"][label].get("color"),
                        outline_width=state_dict["labels"][label].get("outline_width"),
                        outline_color=state_dict["labels"][label].get("outline_color"),
                        alignment=state_dict["labels"][label].get("alignment")
                    )
                    # self.add_label(key_label, position=label, update=False)
                    state.label_manager.set_page_label(label, key_label, update=False)

            ## Load media
            if load_media:
                path = state_dict.get("media", {}).get("path", None)
                if path not in ["", None]:
                    if is_image(path):
                        state.set_image(InputImage(
                            controller_input=self,
                            image=get_page_media_image(path, is_svg_media=False)
                        ), update=False)

                    elif is_svg(path):
                        state.set_image(InputImage(
                            controller_input=self,
                            image=get_page_media_image(path, is_svg_media=True)
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
            if target_state is None:
                self.set_state(old_state_index, persist=False)
            else:
                self.set_state(target_state, allow_reload=True, persist=False)
            self.update()
        else:
            # A key press or release that landed inside a suppression window above
            # never got drawn - draw it now that the state is fully loaded
            self._flush_suppressed_render()

    def set_state(self, state: int, update_sidebar: bool = True, allow_reload: bool = False, persist: bool = True) -> None:
        old_state = self.state
        if state == old_state and not allow_reload:
            return
        super().set_state(state, False, allow_reload, persist)
        if update_sidebar:
            self.reload_sidebar()

    def set_ui_key_image(self, image: Image.Image) -> None:
        if image is None:
            return
        
        x, y = ControllerKey.Index_To_Coords(self.deck_controller.deck, self.index)

        if self.deck_controller.get_own_key_grid() is None or not recursive_hasattr(gl, "app.main_win.get_mapped") or not gl.app.main_win.get_mapped():
            # Save to use later
            self.deck_controller.ui_image_changes_while_hidden[self.identifier] = image # The ui key coords are in reverse order
        else:
            try:
                GLib.idle_add(self.deck_controller.get_own_key_grid().buttons[x][y].set_image, image)
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
        self._pending_ui_image: Image.Image = None
        self._ui_image_update_scheduled = False

    @staticmethod
    def Available_Identifiers(deck):
        if deck.is_touch():
            return ["sd-plus"]
        return []

    def update(self) -> None:
        active_state = self.get_active_state()
        if active_state is None:
            return

        active_state.rebuild_cached_image()
        image = active_state.get_current_image()
        queued_image = image.copy()
        ui_image = image.copy()

        self.deck_controller.media_player.add_touchscreen_task(queued_image)

        self.set_ui_image(ui_image)

    def update_dial_region(self, identifier: Input.Dial, priority: int = TASK_PRIORITY_NORMAL) -> None:
        active_state = self.get_active_state()
        if active_state is None:
            return

        updated_region = active_state.update_dial_region(identifier)
        if updated_region is None:
            self.update()
            return

        area, region = updated_region
        x1, y1, x2, y2 = area
        self.deck_controller.media_player.add_touchscreen_task(
            region,
            x_pos=x1,
            y_pos=y1,
            width=x2 - x1,
            height=y2 - y1,
            priority=priority,
            identifier=identifier,
        )
        self.set_ui_region(identifier, area, active_state.get_current_image())

    def generate_empty_image(self) -> Image.Image:
        return Image.new("RGBA", self.get_screen_dimensions(), (0, 0, 0, 0))
    
    def dials_stack_vertically(self) -> bool:
        # When the deck is rotated onto its side the strip runs vertically, so the
        # dial slots stack along y instead of along x
        return self.deck_controller.deck.get_rotation() % 180 != 0

    def get_dial_image_area(self, identifier: Input.Dial) -> tuple[int, int, int, int]:
        width, height = self.get_screen_dimensions()

        n_dials = len(self.deck_controller.inputs[Input.Dial])
        dial_index = identifier.index

        if self.dials_stack_vertically():
            return (
                0,
                int((dial_index / n_dials) * height),
                width,
                int(((dial_index + 1) / n_dials) * height),
            )

        return (
            int((dial_index / n_dials) * width),
            0,
            int(((dial_index + 1) / n_dials) * width),
            height,
        )

    def get_dial_image_area_size(self) -> tuple[int, int]:
        width, height = self.get_screen_dimensions()

        n_dials = len(self.deck_controller.inputs[Input.Dial])

        if self.dials_stack_vertically():
            return width, int(height / n_dials)

        return int(width / n_dials), height

    def get_empty_dial_image(self) -> Image.Image:
        return Image.new("RGBA", self.get_dial_image_area_size(), (0, 0, 0, 0))

    def set_ui_image(self, image: Image.Image) -> None:
        if (
            not recursive_hasattr(self, "deck_controller.own_deck_stack_child.page_settings.deck_config.screenbar.image")
            or not recursive_hasattr(gl, "app.main_win.get_mapped")
            or not gl.app.main_win.get_mapped()
        ):
            self._store_ui_image_while_hidden(image)
            return

        if self._pending_ui_image is not None:
            self._pending_ui_image.close()

        self._pending_ui_image = image
        if self._ui_image_update_scheduled:
            return

        self._ui_image_update_scheduled = True
        GLib.idle_add(self._flush_ui_image)

    def _flush_ui_image(self):
        self._ui_image_update_scheduled = False
        image = self._pending_ui_image
        self._pending_ui_image = None

        if image is None:
            return False

        if (
            recursive_hasattr(self, "deck_controller.own_deck_stack_child.page_settings.deck_config.screenbar.image")
            and recursive_hasattr(gl, "app.main_win.get_mapped")
            and gl.app.main_win.get_mapped()
        ):
            screenbar = self.deck_controller.own_deck_stack_child.page_settings.deck_config.screenbar
            screenbar.image.set_image(image)
        else:
            self._store_ui_image_while_hidden(image)

        return False

    def set_ui_region(self, identifier: Input.Dial, area: tuple[int, int, int, int], image: Image.Image) -> None:
        if self._ui_image_update_scheduled or self._pending_ui_image is not None:
            self.set_ui_image(image.copy())
            return

        if not recursive_hasattr(self, "deck_controller.own_deck_stack_child.page_settings.deck_config.screenbar.image") or not gl.app.main_win.get_mapped():
            self._store_ui_image_while_hidden(image.copy())
            return

        x1, y1, _, _ = area
        region = image.crop(area)
        screenbar = self.deck_controller.own_deck_stack_child.page_settings.deck_config.screenbar
        GLib.idle_add(screenbar.image.update_region, region, x1, y1, identifier)

    def _store_ui_image_while_hidden(self, image: Image.Image) -> None:
        previous = self.deck_controller.ui_image_changes_while_hidden.get(self.identifier)
        if previous is not None:
            previous.close()
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
            # Along the long axis of the strip - which is y once the deck is rotated
            # onto its side. "Left" is towards the start of the strip either way.
            if self.dials_stack_vertically():
                towards_start = value['y'] > value['y_out']
            else:
                towards_start = value['x'] > value['x_out']

            if towards_start:
                active_state.own_actions_event_callback_threaded(
                    Input.Touchscreen.Events.DRAG_LEFT
                )
            else:
                active_state.own_actions_event_callback_threaded(
                    Input.Touchscreen.Events.DRAG_RIGHT
                )


        #TODO get matching actions from the dials
        elif event_type in (TouchscreenEventType.SHORT, TouchscreenEventType.LONG):
            dial = self.get_dial_for_touch(value['x'], value['y'])
            if dial is not None:
                dial_active_state = dial.get_active_state()
                if dial_active_state is not None:
                    self.deck_controller.media_player.boost_input_priority(dial.identifier)

                    event = Input.Dial.Events.SHORT_TOUCH_PRESS
                    if event_type == TouchscreenEventType.LONG:
                        event = Input.Dial.Events.LONG_TOUCH_PRESS

                    dial_active_state.own_actions_event_callback_threaded(
                        event,
                        data={"x": value['x'], "y": value['y']},
                        show_notifications=True
                    )

    def get_dial_for_touch(self, touch_x: float, touch_y: float = 0) -> "ControllerDial":
        n_dials = len(self.deck_controller.inputs[Input.Dial])
        if n_dials == 0:
            return None

        screen_width, screen_height = self.get_screen_dimensions()
        if self.dials_stack_vertically():
            dial_index = int((touch_y / screen_height) * n_dials)
        else:
            dial_index = int((touch_x / screen_width) * n_dials)

        # A touch right on the far edge would otherwise land one slot past the end
        dial_index = max(0, min(n_dials - 1, dial_index))

        return self.deck_controller.get_input(Input.Dial(str(dial_index)))

    def get_dial_for_touch_x(self, touch_x: float) -> "ControllerDial":
        return self.get_dial_for_touch(touch_x)
    
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
        self.deck_controller.media_player.boost_input_priority(self.identifier)
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

        target_state = self.get_state_to_load(page_dict)
        self.state = 0 if target_state is None else target_state

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
                    font_weight=state_dict["labels"][label].get("font-weight"),
                    style=state_dict["labels"][label].get("style"),
                    color=state_dict["labels"][label].get("color"),
                    alignment=state_dict["labels"][label].get("alignment"),
                )
                state.label_manager.set_page_label(label, key_label, update=False)

            ## Load media
            path = state_dict.get("media", {}).get("path")
            if path not in ["", None]:
                if is_image(path):
                    image = InputImage(
                        controller_input=self,
                        image=get_page_media_image(path, is_svg_media=False),
                    )
                    state.set_image(image, update=False)
                elif is_svg(path):
                    state.set_image(InputImage(
                        controller_input=self,
                        image=get_page_media_image(path, is_svg_media=True)
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
            if target_state is None:
                self.set_state(old_state_index, persist=False)
            else:
                self.set_state(target_state, allow_reload=True, persist=False)
            self.update()

    def update(self, priority: int = TASK_PRIORITY_NORMAL):
        if self.deck_controller.deck.is_touch():
            self.get_touch_screen().update_dial_region(self.identifier, priority=priority)

    def get_active_state(self) -> "ControllerDialState":
        return super().get_active_state()

    def on_media_player_tick(self) -> None:
        self.media_ticks += 1

        state = self.get_active_state()
        if not any([state.video, state.label_manager.get_has_scroll_labels()]):
            return

        self.update(priority=TASK_PRIORITY_LOW)

    def get_image_size(self) -> tuple[int, int]:
        if self.deck_controller.deck.is_touch():
            return self.get_touch_screen().get_dial_image_area_size()
        return (0, 0)
    

class ControllerTouchScreenState(ControllerInputState):
    def __init__(self, controller_touch: "ControllerTouchScreen", state: int):
        super().__init__(controller_touch, state)

        self.controller_touch = controller_touch
        self.base_image: Image.Image = None
        self.current_image: Image.Image = None

    def set_current_image(self, image: Image.Image):
        if self.current_image is not None:
            self.current_image.close()
        self.current_image = image

        self.update()

    def _build_background_image(self) -> Image.Image:
        screen_width, screen_height = self.controller_touch.get_screen_dimensions()
        
        # Start with background image if set
        background: Image.Image = None
        active_page = self.controller_touch.deck_controller.active_page
        background_image_path = active_page.get_background_image(
            identifier=self.controller_touch.identifier, 
            state=self.state
        )
        
        if background_image_path and os.path.isfile(background_image_path):
            try:
                with Image.open(background_image_path) as img:
                    # Resize to exact touchscreen dimensions (KISS - exact dimensions)
                    background = ImageOps.fit(img, (screen_width, screen_height), Image.Resampling.LANCZOS).convert("RGBA")
            except Exception as e:
                log.error(f"Error loading background image: {e}")
                background = None
        
        # Get background color from touchscreen state's background_manager
        background_color = self.background_manager.get_composed_color()
        
        # If no background image, start with empty or colored background
        if background is None:
            # If background color has transparency (alpha < 255), start with transparent
            if background_color[-1] < 255:
                background = self.controller_touch.generate_empty_image()
            
            # If background color is set (alpha > 0), create colored background
            if background_color[-1] > 0:
                background_color_img = Image.new("RGBA", (screen_width, screen_height), color=tuple(background_color))
                
                if background is None:
                    # Use the color as the only background - happens if background color alpha is 255
                    background = background_color_img
                else:
                    # Paste color on top of transparent background
                    background.paste(background_color_img, (0, 0), background_color_img)
            
            # If no background color was set, use empty image
            if background is None:
                background = self.controller_touch.generate_empty_image()
        else:
            # Background image exists - apply color overlay if set
            if background_color[-1] > 0:
                background_color_img = Image.new("RGBA", (screen_width, screen_height), color=tuple(background_color))
                # Blend color over image
                background = Image.alpha_composite(background, background_color_img)

        return background

    def rebuild_cached_image(self) -> None:
        background = self._build_background_image()

        if self.base_image is not None:
            self.base_image.close()
        self.base_image = background

        if self.current_image is not None:
            self.current_image.close()
        self.current_image = background.copy()

        # Paste dial images on top of the background
        for dial in self.controller_touch.deck_controller.inputs[Input.Dial]:
            state = dial.get_active_state()
            image_area = self.controller_touch.get_dial_image_area(dial.identifier)
            dial_image = state.get_rendered_touch_image()

            self.current_image.paste(dial_image, image_area, dial_image)

    def ensure_cached_image(self) -> None:
        if self.base_image is None or self.current_image is None:
            self.rebuild_cached_image()

    def get_current_image(self) -> Image.Image:
        self.ensure_cached_image()
        return self.current_image

    def update_dial_region(self, identifier: Input.Dial) -> tuple[tuple[int, int, int, int], Image.Image] | None:
        self.ensure_cached_image()

        dial = self.controller_touch.deck_controller.get_input(identifier)
        if dial is None:
            return None

        area = self.controller_touch.get_dial_image_area(identifier)
        x1, y1, x2, y2 = area

        region = self.base_image.crop(area)
        dial_state = dial.get_active_state()
        dial_image = dial_state.get_rendered_touch_image()
        region.paste(dial_image, (0, 0), dial_image)
        # Replace the whole dial slot so transparent pixels clear stale content.
        self.current_image.paste(region, (x1, y1))

        return area, region


    def update(self):
        if self.controller_touch.get_active_state() is self:
            self.controller_touch.update()

    

    def set_dial_image(self, identifier: Input.Dial, image: Image.Image, update: bool = True):
        return
        assert isinstance(identifier, Input.Dial)

        area = self.get_dial_image_area(identifier)
        width, height = area[2] - area[0], area[3] - area[1]

        # Clear underground
        empty_dial = self.get_empty_dial_image()
        # Use alpha mask if empty_dial has transparency to prevent edge artifacts
        if empty_dial.has_transparency_data:
            self.current_image.paste(empty_dial, area, empty_dial)
        else:
            self.current_image.paste(empty_dial, area)

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
        if self.base_image is not None:
            self.base_image.close()
        self.base_image = self.controller_touch.generate_empty_image()

    def close_resources(self) -> None:
        if self.current_image is not None:
            self.current_image.close()
            self.current_image = None
        if self.base_image is not None:
            self.base_image.close()
            self.base_image = None

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
            
        # Reset GIF timing
        if isinstance(self.controller_input, ControllerKey):
            self.controller_input.last_gif_update_time = 0
    
    def set_image(self, key_image: "InputImage", update: bool = True) -> None:
        if self.key_image is not None:
            self.key_image.close()
        if self.key_video is not None:
            self.key_video.close()

        self.key_image = key_image
        self.key_video = None

        if update:
            self.update()

    def set_video(self, key_video: "InputVideo") -> None:
        if self.key_video is not None:
            self.key_video.close()
        self.key_video = key_video
        if self.key_image is not None:
            self.key_image.close()
        self.key_image = None
        
        # Reset GIF timing for new video
        if isinstance(self.controller_input, ControllerKey):
            self.controller_input.last_gif_update_time = 0

    def clear(self):
        if self.key_image is not None:
            self.key_image.close()
        if self.key_video is not None:
            self.key_video.close()
        self.key_image = None
        self.key_video = None
        self.label_manager.clear_labels()
        self.layout_manager.clear()
        self.background_manager.set_page_color(None)
