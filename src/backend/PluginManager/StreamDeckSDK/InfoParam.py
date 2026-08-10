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
import platform

import globals as gl

# The Stream Deck software version we report to plugins. Plugins compare their
# manifest's Software.MinimumVersion against it and refuse to run if it is lower, so
# this tracks the newest release the bridge speaks the protocol of.
REPORTED_SOFTWARE_VERSION = "6.9.0"

DEVICE_TYPES = {
    # StreamController deck type -> Stream Deck SDK device type
    "original": 0,
    "mini": 1,
    "xl": 2,
    "mobile": 3,
    "pedal": 5,
    "plus": 7,
    "neo": 9,
}

_SUPPORTED_LANGUAGES = ("en", "de", "es", "fr", "ja", "ko", "zh_CN")


def get_language() -> str:
    language = None
    if gl.lm is not None:
        language = getattr(gl.lm, "language", None) or getattr(gl.lm, "locale", None)

    if not language:
        return "en"

    language = str(language)
    if language in _SUPPORTED_LANGUAGES:
        return language

    short = language.split("_")[0]
    if short in _SUPPORTED_LANGUAGES:
        return short
    return "en"


def get_device_info_list() -> list[dict]:
    devices = []
    if gl.deck_manager is None:
        return devices

    for controller in gl.deck_manager.deck_controller:
        try:
            deck = controller.deck
            rows, columns = deck.key_layout()
            device_type = DEVICE_TYPES.get(_normalize_deck_type(deck.deck_type()), 0)
            devices.append({
                "id": controller.serial_number(),
                "name": deck.deck_type(),
                "size": {"rows": rows, "columns": columns},
                "type": device_type,
            })
        except Exception:
            continue

    return devices


def _normalize_deck_type(deck_type: str) -> str:
    deck_type = (deck_type or "").lower()
    for key in DEVICE_TYPES:
        if key in deck_type:
            return key
    return "original"


def make_info(plugin_uuid: str, plugin_version: str, pretend_windows: bool = False) -> dict:
    """
    Build the ``info`` parameter that is handed to a plugin or property inspector
    during registration.
    """
    return {
        "application": {
            "font": gl.fallback_font or "Sans",
            "language": get_language(),
            "platform": "windows" if pretend_windows else "linux",
            "platformVersion": "10.0.19045" if pretend_windows else platform.release(),
            "version": REPORTED_SOFTWARE_VERSION,
        },
        "plugin": {
            "uuid": plugin_uuid,
            "version": plugin_version,
        },
        "devicePixelRatio": 1,
        "colors": {
            "buttonPressedBackgroundColor": "#303030FF",
            "buttonPressedBorderColor": "#646464FF",
            "buttonPressedTextColor": "#969696FF",
            "disabledColor": "#B5B5B559",
            "highlightColor": "#0092FFFF",
            "mouseDownColor": "#0092FFFF",
        },
        "devices": get_device_info_list(),
    }
