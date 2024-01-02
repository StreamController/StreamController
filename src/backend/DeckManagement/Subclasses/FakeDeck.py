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

class FakeDeck:
    def __init__(self, serial_number = None, deck_type = None):
        self.serial_number = serial_number
        self._deck_type = deck_type
    def deck_type(self):
        return self._deck_type
    def get_serial_number(self):
        return self.serial_number
    def key_layout(self):
        return (3, 5)
    def is_open(self):
        return True
    def reset(self):
        return
    def key_count(self):
        return 15
    def set_key_callback(self, *args, **kwargs):
        return
    def set_brightness(self, *args, **kwargs):
        return
    def set_key_image(self, *args, **kwargs):
        return
    def key_states(self):
        return [False] * 15
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