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

import uuid

import globals as gl

class FakeDeck:
    def __init__(self, serial_number = None, deck_type = None):
        self.serial_number = serial_number
        self._deck_type = deck_type

        self.is_fake = True

        self._key_layout = gl.settings_manager.get_deck_settings(self.serial_number).get("key-layout", [3, 5])
        self._key_layout = [2, 4]

        self._is_touch = True
        self._dial_count = 4

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