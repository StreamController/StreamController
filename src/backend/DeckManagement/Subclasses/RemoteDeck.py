"""
Author: Core447
Year: 2025

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
any later version.

This programm comes with ABSOLUTELY NO WARRANTY!

You should have received a copy of the GNU General Public License
along with this program. If not, see <https://www.gnu.org/licenses/>.
"""

from io import BytesIO
import uuid
from StreamDeck.Devices import StreamDeck
from PIL import Image

import globals as gl

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from src.backend.DeckManagement.Subclasses.RemoteDeckManager import RemoteDeckManager

class RemoteDeck:
    def __init__(self, remote_deck_manager: "RemoteDeckManager", serial_number = None, deck_type = None):
        self.remote_deck_manager: "RemoteDeckManager" = remote_deck_manager
        self.serial_number = serial_number
        self._deck_type = deck_type

        self.is_fake = True

        self._key_layout = [3, 5]

        self._is_touch = False
        self._dial_count = 0

        key_callback: callable = None

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
    def set_key_callback(self, callback: callable):
        self.key_callback = callback
    def set_dial_callback(self, *args, **kwargs):
        return
    def set_touchscreen_callback(self, *args, **kwargs):
        return
    def set_brightness(self, *args, **kwargs):
        return
    def set_key_image(self, key: int, image: bytes):
        pillow_image = Image.open(BytesIO(image))
        pillow_image = pillow_image.rotate(180)
        self.remote_deck_manager.send_button_image(key, pillow_image)
    def key_states(self):
        return [False] * self.key_count()
    def key_image_format(self):
        return {'size': (72, 72), 'format': 'JPEG', 'flip': (True, True), 'rotation': 0}
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
        gl.settings_manager.save_deck_settings(self.serial_number, settings)

    def open(self, *args, **kwargs):
        return
    
    def close(self):
        return
    
    def is_visual(self) -> bool:
        return True
    
    def is_touch(self) -> bool:
        return self.is_touch
    
    def dial_count(self) -> int:
        return self._dial_count
    
    def touchscreen_image_format(self) -> dict:
        return{
            "size": (800, 100),
            "format": "JPEG",
            "flip": (False, False),
            "rotation": 0
        }
    
    def set_touchscreen_image(self, *args, **kwargs):
        return