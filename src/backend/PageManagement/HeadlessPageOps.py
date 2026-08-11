"""
Author: Core447
Year: 2026

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
any later version.

This programm comes with ABSOLUTELY NO WARRANTY!

You should have received a copy of the GNU General Public License
along with this program. If not, see <https://www.gnu.org/licenses/>.
"""
"""
Disk-only page editing used by the CLI when no StreamController instance is
running to answer over DBus.

Page (src/backend/PageManagement/Page.py) cannot be used here: its
load_action_objects() dereferences self.deck_controller.deck unconditionally,
so a Page always needs a live DeckController to even construct. Everything
below instead reads/writes the page JSON directly, mirroring the exact key
layout Page._get_dict_value/_set_dict_value use, so files stay identical
either way. When a StreamController instance is running, the CLI talks to it
over DBus instead (src/api.py), which goes through the real Page methods and
therefore also updates any live UI.
"""
import os

import globals as gl
from src.backend.DeckManagement.InputIdentifier import Input, InputIdentifier

# CLI property name -> JSON key under states.<n>.labels.<position>
LABEL_PROPERTIES = {
    "text": "text",
    "font-family": "font-family",
    "font-size": "font-size",
    "font-style": "font-style",
    "font-weight": "font-weight",
    "color": "color",
    "outline-width": "outline_width",
    "outline-color": "outline_color",
    "align": "alignment",
}

# CLI property name -> JSON key under states.<n>.media
MEDIA_PROPERTIES = {
    "path": "path",
    "size": "size",
    "valign": "valign",
    "halign": "halign",
    "fill-mode": "fill-mode",
}

# CLI property name -> Page.get_label_<x>()/set_label_<x>() method suffix.
# Only used by the live (DBus-backed) path in src/api.py - the JSON key
# (LABEL_PROPERTIES above) is what headless mode reads/writes directly.
LABEL_METHOD = {
    "text": "text",
    "font-family": "font_family",
    "font-size": "font_size",
    "font-style": "font_style",
    "font-weight": "font_weight",
    "color": "font_color",
    "outline-width": "outline_width",
    "outline-color": "outline_color",
    "align": "alignment",
}

# CLI property name -> Page.get_media_<x>()/set_media_<x>() method suffix.
MEDIA_METHOD = {
    "path": "path",
    "size": "size",
    "valign": "valign",
    "halign": "halign",
    "fill-mode": "fill_mode",
}

LABEL_POSITIONS = ("top", "center", "bottom")

# Value types, keyed the same way as LABEL_PROPERTIES/MEDIA_PROPERTIES,
# used to coerce a raw CLI string into the type the page JSON expects.
LABEL_VALUE_TYPES = {
    "text": "str",
    "font-family": "str",
    "font-size": "int",
    "font-style": "str",
    "font-weight": "int",
    "color": "color",
    "outline-width": "int",
    "outline-color": "color",
    "align": "str",
}
MEDIA_VALUE_TYPES = {
    "path": "str",
    "size": "float",
    "valign": "float",
    "halign": "float",
    "fill-mode": "str",
}


def parse_color(raw: str) -> list[int]:
    try:
        parts = [int(p.strip()) for p in raw.split(",")]
    except ValueError:
        raise HeadlessOpError(f"Invalid color '{raw}'. Expected format: 'R,G,B' or 'R,G,B,A' (0-255)")
    if len(parts) == 3:
        parts.append(255)
    if len(parts) != 4 or any(p < 0 or p > 255 for p in parts):
        raise HeadlessOpError(f"Invalid color '{raw}'. Expected format: 'R,G,B' or 'R,G,B,A' (0-255)")
    return parts


def _coerce(value_type: str, raw: str):
    try:
        if value_type == "int":
            return int(raw)
        if value_type == "float":
            return float(raw)
        if value_type == "color":
            return parse_color(raw)
        return raw
    except ValueError:
        raise HeadlessOpError(f"Invalid value '{raw}' for a {value_type} property")


def coerce_label_value(prop: str, raw: str):
    return _coerce(LABEL_VALUE_TYPES[prop], raw)


def coerce_media_value(prop: str, raw: str):
    return _coerce(MEDIA_VALUE_TYPES[prop], raw)


def format_value(value) -> str:
    """Human-readable rendering of a stored property value for CLI output."""
    if isinstance(value, list):
        return ",".join(str(v) for v in value)
    if value is None:
        return ""
    return str(value)


class HeadlessOpError(Exception):
    """Raised for any failure a CLI caller should see as an error, not a crash."""


class _StubDeckManager:
    """Satisfies `for controller in gl.deck_manager.deck_controller` in
    PageManagerBackend.move_page/remove_page when nothing is actually connected."""
    deck_controller = []


def bootstrap():
    """Populates just enough of globals.py for PageManagerBackend/AssetManagerBackend
    to work without booting the GTK app or touching any hardware."""
    if gl.settings_manager is None:
        from src.backend.SettingsManager import SettingsManager
        gl.settings_manager = SettingsManager()

    if gl.deck_manager is None:
        gl.deck_manager = _StubDeckManager()

    if gl.page_manager is None:
        from src.backend.PageManagement.PageManagerBackend import PageManagerBackend
        gl.page_manager = PageManagerBackend(gl.settings_manager)


def bootstrap_asset_manager():
    """Only needed for --set-icon - pulls in MediaManager/AssetManagerBackend."""
    bootstrap()
    if gl.media_manager is None:
        from src.backend.MediaManager import MediaManager
        gl.media_manager = MediaManager()
    if gl.asset_manager_backend is None:
        from src.backend.AssetManagerBackend import AssetManagerBackend
        gl.asset_manager_backend = AssetManagerBackend()


def resolve_page_path(name: str) -> str | None:
    bootstrap()
    return gl.page_manager.find_matching_page_path(name)


def identifier_from_coords(coords: str) -> InputIdentifier:
    try:
        x, y = coords.split(",")
        int(x), int(y)
    except ValueError:
        raise HeadlessOpError(f"Invalid coordinate format '{coords}'. Expected format: 'x,y' (e.g. '0,0')")
    return Input.Key(f"{x}x{y}")


def _get_nested(data: dict, keys: list[str]):
    value = data
    for i, key in enumerate(keys):
        if not isinstance(value, dict):
            return None
        value = value.get(key)
    return value


def _set_nested(data: dict, keys: list[str], value) -> None:
    d = data
    for key in keys[:-1]:
        d = d.setdefault(key, {})
    d[keys[-1]] = value


def _load_page_dict(page_path: str) -> dict:
    bootstrap()
    return gl.page_manager.get_page_data(page_path)


def _save_page_dict(page_path: str, data: dict) -> None:
    gl.page_manager.set_page_data(
        page_path, data,
        reload_brightness=False, reload_screensaver=False,
        reload_background=False, reload_inputs=False,
    )


def _state_dict(data: dict, identifier: InputIdentifier, state: int, create: bool = False) -> dict | None:
    input_dict = data.get(identifier.input_type, {}).get(identifier.json_identifier)
    if input_dict is None:
        if not create:
            return None
        input_dict = data.setdefault(identifier.input_type, {}).setdefault(identifier.json_identifier, {})

    states = input_dict.setdefault("states", {}) if create else input_dict.get("states", {})
    state_dict = states.get(str(state))
    if state_dict is None:
        if not create:
            return None
        state_dict = states.setdefault(str(state), {})
    return state_dict


# ── Pages ────────────────────────────────────────────────────────────

def create_page(name: str) -> str:
    bootstrap()
    try:
        return gl.page_manager.add_page(name)
    except FileExistsError as e:
        raise HeadlessOpError(str(e))


def delete_page(page_path: str) -> None:
    bootstrap()
    gl.page_manager.remove_page(page_path)


def rename_page(page_path: str, new_name: str) -> str:
    bootstrap()
    new_path = os.path.join(gl.page_manager.PAGE_PATH, f"{new_name}.json")
    if os.path.exists(new_path):
        raise HeadlessOpError(f"A page with the name '{new_name}' already exists.")
    gl.page_manager.move_page(page_path, new_path)
    return new_path


def duplicate_page(page_path: str, new_name: str) -> str:
    bootstrap()
    data = gl.page_manager.get_page_data(page_path)
    try:
        return gl.page_manager.add_page(new_name, data)
    except FileExistsError as e:
        raise HeadlessOpError(str(e))


# ── States ───────────────────────────────────────────────────────────

def add_state(page_path: str, coords: str) -> int:
    identifier = identifier_from_coords(coords)
    data = _load_page_dict(page_path)
    state_dict = data.setdefault(identifier.input_type, {}).setdefault(identifier.json_identifier, {})
    states = state_dict.setdefault("states", {})
    if not states:
        # An input always has a state 0, even when the page json has no entry for
        # it yet - same as DeckController.ControllerInput.add_new_state(), which
        # writes out every state it holds, including the implicit first one
        states["0"] = {}
    new_index = len(states)
    states[str(new_index)] = {}
    _save_page_dict(page_path, data)
    return new_index


def remove_state(page_path: str, coords: str, state: int) -> None:
    identifier = identifier_from_coords(coords)
    data = _load_page_dict(page_path)
    input_dict = data.get(identifier.input_type, {}).get(identifier.json_identifier)
    if input_dict is None or str(state) not in input_dict.get("states", {}):
        raise HeadlessOpError(f"State {state} does not exist at {coords}")

    states = input_dict["states"]
    states.pop(str(state))

    # Re-index remaining states to stay contiguous, same as
    # DeckController.ControllerInput.remove_state()
    reindexed = {}
    for new_key, old_key in enumerate(sorted(states.keys(), key=int)):
        reindexed[str(new_key)] = states[old_key]
    input_dict["states"] = reindexed

    _save_page_dict(page_path, data)


# ── Labels ───────────────────────────────────────────────────────────

def get_label(page_path: str, coords: str, state: int, position: str, prop: str):
    if position not in LABEL_POSITIONS:
        raise HeadlessOpError(f"Invalid label position '{position}'. Must be one of: {', '.join(LABEL_POSITIONS)}")
    if prop not in LABEL_PROPERTIES:
        raise HeadlessOpError(f"Invalid label property '{prop}'. Must be one of: {', '.join(LABEL_PROPERTIES)}")

    identifier = identifier_from_coords(coords)
    data = _load_page_dict(page_path)
    state_dict = _state_dict(data, identifier, state) or {}
    return _get_nested(state_dict, ["labels", position, LABEL_PROPERTIES[prop]])


def set_label(page_path: str, coords: str, state: int, position: str, prop: str, raw_value: str) -> None:
    if position not in LABEL_POSITIONS:
        raise HeadlessOpError(f"Invalid label position '{position}'. Must be one of: {', '.join(LABEL_POSITIONS)}")
    if prop not in LABEL_PROPERTIES:
        raise HeadlessOpError(f"Invalid label property '{prop}'. Must be one of: {', '.join(LABEL_PROPERTIES)}")

    value = coerce_label_value(prop, raw_value)
    identifier = identifier_from_coords(coords)
    data = _load_page_dict(page_path)
    state_dict = _state_dict(data, identifier, state, create=True)
    _set_nested(state_dict, ["labels", position, LABEL_PROPERTIES[prop]], value)
    _save_page_dict(page_path, data)


# ── Background color ────────────────────────────────────────────────

def get_background_color(page_path: str, coords: str, state: int) -> list[int] | None:
    identifier = identifier_from_coords(coords)
    data = _load_page_dict(page_path)
    state_dict = _state_dict(data, identifier, state) or {}
    return _get_nested(state_dict, ["background", "color"])


def set_background_color(page_path: str, coords: str, state: int, raw_color: str) -> None:
    color = parse_color(raw_color)
    identifier = identifier_from_coords(coords)
    data = _load_page_dict(page_path)
    state_dict = _state_dict(data, identifier, state, create=True)
    _set_nested(state_dict, ["background", "color"], color)
    _save_page_dict(page_path, data)


# ── Media / icon ─────────────────────────────────────────────────────

def get_media(page_path: str, coords: str, state: int, prop: str):
    if prop not in MEDIA_PROPERTIES:
        raise HeadlessOpError(f"Invalid media property '{prop}'. Must be one of: {', '.join(MEDIA_PROPERTIES)}")

    identifier = identifier_from_coords(coords)
    data = _load_page_dict(page_path)
    state_dict = _state_dict(data, identifier, state) or {}
    return _get_nested(state_dict, ["media", MEDIA_PROPERTIES[prop]])


def set_media(page_path: str, coords: str, state: int, prop: str, raw_value: str) -> None:
    if prop not in MEDIA_PROPERTIES:
        raise HeadlessOpError(f"Invalid media property '{prop}'. Must be one of: {', '.join(MEDIA_PROPERTIES)}")

    value = coerce_media_value(prop, raw_value)
    identifier = identifier_from_coords(coords)
    data = _load_page_dict(page_path)
    state_dict = _state_dict(data, identifier, state, create=True)
    _set_nested(state_dict, ["media", MEDIA_PROPERTIES[prop]], value)
    _save_page_dict(page_path, data)


def set_icon(page_path: str, coords: str, state: int, source_path: str) -> str:
    if not os.path.isfile(source_path):
        raise HeadlessOpError(f"File not found: {source_path}")

    bootstrap_asset_manager()
    asset_id = gl.asset_manager_backend.add(source_path)
    if asset_id is None:
        raise HeadlessOpError(f"'{source_path}' could not be added as an asset (unsupported/undecodable file)")

    internal_path = gl.asset_manager_backend.get_by_id(asset_id)["internal-path"]
    set_media(page_path, coords, state, "path", internal_path)
    return internal_path
