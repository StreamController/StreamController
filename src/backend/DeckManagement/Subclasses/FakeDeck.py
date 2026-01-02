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


def _extract_deck_specs_from_library():

    specs = {}
    
    try:
        # Import all device classes
        from StreamDeck.Devices.StreamDeckOriginal import StreamDeckOriginal
        from StreamDeck.Devices.StreamDeckMini import StreamDeckMini
        from StreamDeck.Devices.StreamDeckXL import StreamDeckXL
        from StreamDeck.Devices.StreamDeckPlus import StreamDeckPlus
        from StreamDeck.Devices.StreamDeckNeo import StreamDeckNeo
        import StreamDeck.Devices.StreamDeckOriginalV2
        
        device_classes = [
            StreamDeckOriginal,
            StreamDeck.Devices.StreamDeckOriginalV2.StreamDeckOriginalV2,
            StreamDeckMini,
            StreamDeckXL,
            StreamDeckPlus,
            StreamDeckNeo,
        ]
        
        # Extract specs from each device class
        for device_class in device_classes:
            try:
                deck_type_name = device_class.DECK_TYPE
                key_layout = [device_class.KEY_ROWS, device_class.KEY_COLS]
                key_image_size = (device_class.KEY_PIXEL_WIDTH, device_class.KEY_PIXEL_HEIGHT)
                dial_count = getattr(device_class, 'DIAL_COUNT', 0)
                
                # Check for touchscreen support
                has_touch = getattr(device_class, 'DECK_TOUCH', False)
                touchscreen_format = getattr(device_class, 'TOUCHSCREEN_IMAGE_FORMAT', None)
                has_touchscreen = touchscreen_format is not None and touchscreen_format != ''
                
                touchscreen_size = None
                if has_touchscreen:
                    touchscreen_width = getattr(device_class, 'TOUCHSCREEN_PIXEL_WIDTH', None)
                    touchscreen_height = getattr(device_class, 'TOUCHSCREEN_PIXEL_HEIGHT', None)
                    if touchscreen_width and touchscreen_height:
                        touchscreen_size = (touchscreen_width, touchscreen_height)
                
                spec = {
                    "key_layout": key_layout,
                    "key_image_size": key_image_size,
                    "has_touch": has_touch,
                    "dial_count": dial_count,
                    "has_touchscreen": has_touchscreen,
                }
                
                if touchscreen_size:
                    spec["touchscreen_size"] = touchscreen_size
                
                specs[deck_type_name] = spec
                
            except Exception as e:
                # If we can't extract specs for this device type, skip it
                continue
                
    except ImportError as e:
        # If device classes can't be imported, return empty dict
        # This should not happen in normal operation
        pass
    
    return specs


# Cache the specs at module level so we only extract once
_DECK_SPECS = None

def get_deck_specs():
    """Get deck specifications, caching the result."""
    global _DECK_SPECS
    if _DECK_SPECS is None:
        _DECK_SPECS = _extract_deck_specs_from_library()
    return _DECK_SPECS


def get_available_deck_types():
    """Get list of available deck type names."""
    specs = get_deck_specs()
    return list(specs.keys())


class FakeDeck:
    def __init__(self, serial_number = None, deck_type = None):
        self.serial_number = serial_number
        self._deck_type = deck_type

        self.is_fake = True

        # Get specs from the library for this deck type
        specs_dict = get_deck_specs()
        specs = specs_dict.get(deck_type, {
            "key_layout": [3, 5],
            "key_image_size": (72, 72),
            "has_touch": False,
            "dial_count": 0,
            "has_touchscreen": False,
        })
        
        # Load key layout from settings or use spec default
        self._key_layout = gl.settings_manager.get_deck_settings(self.serial_number).get("key-layout", specs["key_layout"])
        
        self._key_image_size = specs["key_image_size"]
        self._is_touch = specs.get("has_touch", False)
        self._dial_count = specs.get("dial_count", 0)
        self._has_touchscreen = specs.get("has_touchscreen", False)
        self._touchscreen_size = specs.get("touchscreen_size", (800, 100))

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
        return {'size': self._key_image_size, 'format': 'JPEG', 'flip': (True, True), 'rotation': 0}
    
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
        return self._is_touch
    
    def dial_count(self) -> int:
        return self._dial_count
    
    def touchscreen_image_format(self) -> dict:
        if not self._has_touchscreen:
            return None
        return {
            "size": self._touchscreen_size,
            "format": "JPEG",
            "flip": (False, False),
            "rotation": 0
        }
    
    def set_touchscreen_image(self, *args, **kwargs):
        return
