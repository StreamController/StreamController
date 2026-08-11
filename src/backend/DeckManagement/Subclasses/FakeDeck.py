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

import importlib
import pkgutil
import uuid
from functools import lru_cache

from loguru import logger as log

import StreamDeck.Devices as StreamDeckDevices
from StreamDeck.Devices.StreamDeck import StreamDeck
from StreamDeck.Devices.StreamDeckPlus import StreamDeckPlus

import globals as gl

DEFAULT_FAKE_DECK_TYPE = StreamDeckPlus.DECK_TYPE


def _all_subclasses(cls: type) -> list[type]:
    subclasses = []
    for subclass in cls.__subclasses__():
        subclasses.append(subclass)
        subclasses.extend(_all_subclasses(subclass))
    return subclasses


@lru_cache(maxsize=None)
def get_supported_deck_classes() -> tuple[type[StreamDeck], ...]:
    """
    Every deck model the StreamDeck library knows about, i.e. everything a fake
    deck can emulate. The modules of the library are imported here because the
    device classes only register themselves as subclasses once their module was
    imported.
    """
    for module in pkgutil.iter_modules(StreamDeckDevices.__path__):
        try:
            importlib.import_module(f"{StreamDeckDevices.__name__}.{module.name}")
        except Exception as e:
            log.error(f"Failed to import deck module {module.name}. Error: {e}")

    # Some models share a deck type (eg. the original and its v2) - one entry per
    # model name is enough for a fake deck
    classes: dict[str, type[StreamDeck]] = {}
    for deck_class in _all_subclasses(StreamDeck):
        if not deck_class.DECK_TYPE:
            continue
        classes.setdefault(deck_class.DECK_TYPE, deck_class)

    return tuple(sorted(classes.values(), key=lambda deck_class: deck_class.DECK_TYPE))


def get_supported_deck_types() -> list[str]:
    return [deck_class.DECK_TYPE for deck_class in get_supported_deck_classes()]


def get_deck_class_for_type(deck_type: str) -> type[StreamDeck] | None:
    for deck_class in get_supported_deck_classes():
        if deck_class.DECK_TYPE == deck_type:
            return deck_class
    return None


class FakeDeck:
    """
    Emulates one of the supported deck models without any hardware attached.
    All properties are taken from the emulated model, so a fake deck behaves
    like the real thing everywhere in the app.
    """
    def __init__(self, serial_number = None, deck_type = None):
        self.serial_number = serial_number

        self.emulated_class: type[StreamDeck] = get_deck_class_for_type(deck_type)
        if self.emulated_class is None:
            if deck_type is not None:
                log.warning(f"Unknown deck type for fake deck: {deck_type}. Falling back to {DEFAULT_FAKE_DECK_TYPE}")
            self.emulated_class = get_deck_class_for_type(DEFAULT_FAKE_DECK_TYPE)

        self.model_name: str = self.emulated_class.DECK_TYPE
        self._deck_type = f"Fake {self.model_name}"

        self.is_fake = True

        self._key_layout = self.load_key_layout()

    def load_key_layout(self) -> list[int]:
        """
        Layout of the emulated model, unless the user set a custom one for this
        model (see set_key_layout)
        """
        settings = gl.settings_manager.get_deck_settings(self.serial_number)
        if settings.get("fake-deck-type") == self.model_name:
            layout = settings.get("key-layout")
            if layout:
                return list(layout)

        return [self.emulated_class.KEY_ROWS, self.emulated_class.KEY_COLS]

    def deck_type(self):
        return self._deck_type
    def get_serial_number(self):
        return self.serial_number
    def key_layout(self):
        return self._key_layout
    def is_open(self):
        return True
    def reset(self):
        return
    def key_count(self):
        return self.key_layout()[0] * self.key_layout()[1]
    def touch_key_count(self):
        return self.emulated_class.TOUCH_KEY_COUNT
    def set_key_callback(self, *args, **kwargs):
        return
    def set_dial_callback(self, *args, **kwargs):
        return
    def set_touchscreen_callback(self, *args, **kwargs):
        return
    def set_brightness(self, *args, **kwargs):
        return
    def set_key_image(self, *args, **kwargs):
        return
    def set_key_color(self, *args, **kwargs):
        return
    def key_states(self):
        return [False] * (self.key_count() + self.touch_key_count())
    def key_image_format(self):
        return {
            "size": (self.emulated_class.KEY_PIXEL_WIDTH, self.emulated_class.KEY_PIXEL_HEIGHT),
            "format": self.emulated_class.KEY_IMAGE_FORMAT,
            "flip": self.emulated_class.KEY_FLIP,
            "rotation": self.emulated_class.KEY_ROTATION
        }
    def id(self):
        return str(uuid.uuid4())
    def connected(self):
        return True
    def __enter__(self):
        return self
    def __exit__(self, exc_type, exc_val, exc_tb):
        return True

    def set_key_layout(self, layout: list[int]):
        """
        Sets and saves a new key layout
        """
        self._key_layout = layout

        settings = gl.settings_manager.get_deck_settings(self.serial_number)
        settings["key-layout"] = layout
        # The layout only applies to the model it was set for - switching the
        # emulated model has to bring its own layout with it
        settings["fake-deck-type"] = self.model_name
        gl.settings_manager.save_deck_settings(self.serial_number, settings)

    def open(self, *args, **kwargs):
        return

    def close(self):
        return

    def is_visual(self) -> bool:
        return self.emulated_class.DECK_VISUAL

    def is_touch(self) -> bool:
        return self.emulated_class.DECK_TOUCH

    def dial_count(self) -> int:
        return self.emulated_class.DIAL_COUNT

    def touchscreen_image_format(self) -> dict:
        return {
            "size": (self.emulated_class.TOUCHSCREEN_PIXEL_WIDTH, self.emulated_class.TOUCHSCREEN_PIXEL_HEIGHT),
            "format": self.emulated_class.TOUCHSCREEN_IMAGE_FORMAT,
            "flip": self.emulated_class.TOUCHSCREEN_FLIP,
            "rotation": self.emulated_class.TOUCHSCREEN_ROTATION
        }

    def set_touchscreen_image(self, *args, **kwargs):
        return

    def screen_image_format(self) -> dict:
        return {
            "size": (self.emulated_class.SCREEN_PIXEL_WIDTH, self.emulated_class.SCREEN_PIXEL_HEIGHT),
            "format": self.emulated_class.SCREEN_IMAGE_FORMAT,
            "flip": self.emulated_class.SCREEN_FLIP,
            "rotation": self.emulated_class.SCREEN_ROTATION
        }

    def set_screen_image(self, *args, **kwargs):
        return
