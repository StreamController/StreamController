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
import os
import uuid

from PIL import Image, ImageDraw

from loguru import logger as log

import globals as gl

from src.backend.DeckManagement.InputIdentifier import Input
from src.backend.PluginManager.ActionCore import ActionCore
from src.backend.PluginManager.EventAssigner import EventAssigner
from src.backend.PluginManager.StreamDeckSDK.Images import load_image, parse_color
from src.backend.PluginManager.StreamDeckSDK.Manifest import SDAction as SDActionManifest

# Where the alignment of a Stream Deck title ends up in StreamController's label slots
TITLE_ALIGNMENT_TO_POSITION = {
    "top": "top",
    "middle": "center",
    "bottom": "bottom",
}

SETTINGS_KEY = "sdk-settings"
STATE_KEY = "sdk-state"

# Stream Deck font sizes assume a 72x72 tile
REFERENCE_TILE_SIZE = 72


class SDActionCore(ActionCore):
    """
    Bridges a single action of a Stream Deck SDK plugin into StreamController.

    One instance corresponds to one action placed on a key or dial, which is what the
    SDK calls a *context*.
    """

    # Set on the subclass generated for each action in a plugin manifest
    SD_ACTION: SDActionManifest = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.sd_action: SDActionManifest = type(self).SD_ACTION
        self.sd_context: str = uuid.uuid4().hex

        self.sd_state: int = 0
        self.sd_title_overrides: dict[int, str] = {}
        self.sd_image_overrides: dict[int, str] = {}
        self.sd_feedback: dict = {}

        self._appeared: bool = False
        self._settings_loaded: bool = False
        self._property_inspector = None

        # Everything configurable about these actions lives in their property inspector
        self.has_configuration = self.get_property_inspector_path() is not None

        self._add_event_assigners()

        gl.sd_sdk_manager.register_context(self)

    # -------------- #
    # Plugin linkage #
    # -------------- #

    @property
    def sd_plugin(self):
        """The SDPluginBase this action belongs to."""
        return self.plugin_base

    @property
    def plugin_path(self) -> str:
        return self.sd_plugin.sd_manifest.path

    @property
    def plugin_uuid(self) -> str:
        return self.sd_plugin.sd_manifest.uuid

    # ---------------- #
    # Event assigners  #
    # ---------------- #

    def _add_event_assigners(self) -> None:
        self.add_event_assigner(EventAssigner(
            id="sdk-key-down",
            ui_label="Key Down",
            tooltip="Sends keyDown to the plugin",
            default_events=[Input.Key.Events.DOWN],
            callback=lambda data: self._on_key_down(),
        ))
        self.add_event_assigner(EventAssigner(
            id="sdk-key-up",
            ui_label="Key Up",
            tooltip="Sends keyUp to the plugin",
            default_events=[Input.Key.Events.UP],
            callback=lambda data: self._on_key_up(),
        ))

        self.add_event_assigner(EventAssigner(
            id="sdk-dial-down",
            ui_label="Dial Down",
            tooltip="Sends dialDown to the plugin",
            default_events=[Input.Dial.Events.DOWN],
            callback=lambda data: self._send_dial_press("dialDown"),
        ))
        self.add_event_assigner(EventAssigner(
            id="sdk-dial-up",
            ui_label="Dial Up",
            tooltip="Sends dialUp to the plugin",
            default_events=[Input.Dial.Events.UP],
            callback=lambda data: self._send_dial_press("dialUp"),
        ))
        self.add_event_assigner(EventAssigner(
            id="sdk-dial-turn-cw",
            ui_label="Dial Turn Clockwise",
            tooltip="Sends dialRotate with a positive tick count",
            default_events=[Input.Dial.Events.TURN_CW],
            callback=lambda data: self._send_dial_rotate(1),
        ))
        self.add_event_assigner(EventAssigner(
            id="sdk-dial-turn-ccw",
            ui_label="Dial Turn Counterclockwise",
            tooltip="Sends dialRotate with a negative tick count",
            default_events=[Input.Dial.Events.TURN_CCW],
            callback=lambda data: self._send_dial_rotate(-1),
        ))
        self.add_event_assigner(EventAssigner(
            id="sdk-touch-tap",
            ui_label="Touchscreen Tap",
            tooltip="Sends touchTap to the plugin",
            default_events=[Input.Dial.Events.SHORT_TOUCH_PRESS],
            callback=lambda data: self._send_touch_tap(data, hold=False),
        ))
        self.add_event_assigner(EventAssigner(
            id="sdk-touch-hold",
            ui_label="Touchscreen Long Press",
            tooltip="Sends touchTap with hold set to true",
            default_events=[Input.Dial.Events.LONG_TOUCH_PRESS],
            callback=lambda data: self._send_touch_tap(data, hold=True),
        ))

    # -------------- #
    # SDK identifiers #
    # -------------- #

    def get_device_id(self) -> str:
        if self.deck_controller is None:
            return ""
        try:
            return self.deck_controller.serial_number()
        except Exception:
            return ""

    def get_controller_name(self) -> str:
        return "Encoder" if isinstance(self.input_ident, Input.Dial) else "Keypad"

    def get_coordinates(self) -> dict:
        if isinstance(self.input_ident, Input.Key):
            column, row = self.input_ident.coords
            return {"row": row, "column": column}
        if isinstance(self.input_ident, Input.Dial):
            return {"row": 0, "column": self.input_ident.index}
        return {"row": 0, "column": 0}

    def get_generic_payload(self) -> dict:
        return {
            "settings": self.get_sd_settings(),
            "coordinates": self.get_coordinates(),
            "controller": self.get_controller_name(),
            "state": self.sd_state,
            "isInMultiAction": False,
        }

    def get_action_info(self) -> dict:
        """The ``actionInfo`` parameter handed to the property inspector."""
        return {
            "action": self.sd_action.uuid,
            "context": self.sd_context,
            "device": self.get_device_id(),
            "payload": self.get_generic_payload(),
        }

    # -------- #
    # Settings #
    # -------- #

    def get_sd_settings(self) -> dict:
        settings = self.get_settings() or {}
        return settings.get(SETTINGS_KEY) or {}

    def set_sd_settings(self, sd_settings: dict) -> None:
        settings = self.get_settings() or {}
        settings[SETTINGS_KEY] = sd_settings
        settings[STATE_KEY] = self.sd_state
        self.set_settings(settings)

    def _persist_state(self) -> None:
        settings = self.get_settings() or {}
        if settings.get(STATE_KEY) == self.sd_state:
            return
        settings[STATE_KEY] = self.sd_state
        self.set_settings(settings)

    def _load_persisted_state(self) -> None:
        if self._settings_loaded:
            return
        self._settings_loaded = True

        stored = (self.get_settings() or {}).get(STATE_KEY)
        if isinstance(stored, int) and 0 <= stored < len(self.sd_action.states):
            self.sd_state = stored

    # -------------- #
    # StreamController lifecycle #
    # -------------- #

    def on_ready(self) -> None:
        self._load_persisted_state()
        self.render()
        self.send_will_appear()

    def on_update(self) -> None:
        self.render()

    def on_removed_from_cache(self) -> None:
        self._teardown()

    def on_remove(self) -> None:
        self._teardown()

    def _teardown(self) -> None:
        self.send_will_disappear()
        gl.sd_sdk_manager.unregister_context(self)

    # --------------- #
    # Outbound events #
    # --------------- #

    def _send(self, event: str, payload: dict = None, extra: dict = None) -> None:
        message = {
            "event": event,
            "action": self.sd_action.uuid,
            "context": self.sd_context,
            "device": self.get_device_id(),
        }
        if payload is not None:
            message["payload"] = payload
        if extra:
            message.update(extra)

        gl.sd_sdk_manager.send_to_plugin(self.plugin_uuid, message)

    def send_will_appear(self) -> None:
        if self._appeared:
            return
        self._appeared = True
        self._send("willAppear", self.get_generic_payload())
        self.send_title_parameters_did_change()

    def resend_will_appear(self) -> None:
        """Announce this action again, e.g. after its plugin reconnected."""
        self._appeared = False
        self.send_will_appear()

    def send_will_disappear(self) -> None:
        if not self._appeared:
            return
        self._appeared = False
        self._send("willDisappear", self.get_generic_payload())

    def send_did_receive_settings(self) -> None:
        payload = self.get_generic_payload()
        self._send("didReceiveSettings", payload)
        gl.sd_sdk_manager.send_to_property_inspector(self.sd_context, {
            "event": "didReceiveSettings",
            "action": self.sd_action.uuid,
            "context": self.sd_context,
            "device": self.get_device_id(),
            "payload": payload,
        })

    def send_title_parameters_did_change(self) -> None:
        manifest_state = self.get_manifest_state()
        payload = self.get_generic_payload()
        payload["title"] = self.sd_title_overrides.get(self.sd_state, manifest_state.title)
        payload["titleParameters"] = {
            "fontFamily": manifest_state.font_family,
            "fontSize": manifest_state.font_size,
            "fontStyle": manifest_state.font_style,
            "fontUnderline": manifest_state.font_underline,
            "showTitle": manifest_state.show_title,
            "titleAlignment": manifest_state.title_alignment,
            "titleColor": manifest_state.title_color,
        }
        self._send("titleParametersDidChange", payload)

    def _on_key_down(self) -> None:
        self._send("keyDown", self.get_generic_payload())

    def _on_key_up(self) -> None:
        self._send("keyUp", self.get_generic_payload())

        # The Stream Deck software flips between the two states of a two state action
        # by itself unless the action opted out
        if len(self.sd_action.states) == 2 and not self.sd_action.disable_automatic_states:
            self.sd_state = (self.sd_state + 1) % 2
            self._persist_state()
            self.render()

    def _send_dial_press(self, event: str) -> None:
        payload = {
            "controller": "Encoder",
            "settings": self.get_sd_settings(),
            "coordinates": self.get_coordinates(),
        }
        self._send(event, payload)

    def _send_dial_rotate(self, ticks: int) -> None:
        try:
            pressed = bool(getattr(self.get_input(), "press_state", False))
        except Exception:
            pressed = False

        payload = {
            "controller": "Encoder",
            "settings": self.get_sd_settings(),
            "coordinates": self.get_coordinates(),
            "ticks": ticks,
            "pressed": pressed,
        }
        self._send("dialRotate", payload)

    def _send_touch_tap(self, data: dict, hold: bool) -> None:
        data = data or {}
        payload = {
            "controller": "Encoder",
            "settings": self.get_sd_settings(),
            "coordinates": self.get_coordinates(),
            "tapPos": [int(data.get("x", 0)), int(data.get("y", 0))],
            "hold": hold,
        }
        self._send("touchTap", payload)

    # -------------- #
    # Inbound events #
    # -------------- #

    def handle_set_title(self, payload: dict) -> None:
        title = payload.get("title")
        state = payload.get("state")

        states = range(len(self.sd_action.states)) if state is None else [state]
        for index in states:
            if not 0 <= index < len(self.sd_action.states):
                continue
            if title is None:
                self.sd_title_overrides.pop(index, None)
            else:
                self.sd_title_overrides[index] = str(title)

        self.render()

    def handle_set_image(self, payload: dict) -> None:
        image = payload.get("image")
        state = payload.get("state")

        states = range(len(self.sd_action.states)) if state is None else [state]
        for index in states:
            if not 0 <= index < len(self.sd_action.states):
                continue
            if image is None or (isinstance(image, str) and not image.strip()):
                self.sd_image_overrides.pop(index, None)
            else:
                self.sd_image_overrides[index] = image

        self.render()

    def handle_set_state(self, payload: dict) -> None:
        state = payload.get("state")
        if not isinstance(state, int) or not 0 <= state < len(self.sd_action.states):
            return
        self.sd_state = state
        self._persist_state()
        self.render()
        self.send_title_parameters_did_change()

    def handle_set_settings(self, payload: dict, from_property_inspector: bool) -> None:
        if not isinstance(payload, dict):
            return
        self.set_sd_settings(payload)

        # The sender does not get its own settings echoed back to it
        response = {
            "event": "didReceiveSettings",
            "action": self.sd_action.uuid,
            "context": self.sd_context,
            "device": self.get_device_id(),
            "payload": self.get_generic_payload(),
        }
        if from_property_inspector:
            gl.sd_sdk_manager.send_to_plugin(self.plugin_uuid, response)
        else:
            gl.sd_sdk_manager.send_to_property_inspector(self.sd_context, response)

    def handle_get_settings(self, from_property_inspector: bool) -> None:
        response = {
            "event": "didReceiveSettings",
            "action": self.sd_action.uuid,
            "context": self.sd_context,
            "device": self.get_device_id(),
            "payload": self.get_generic_payload(),
        }
        if from_property_inspector:
            gl.sd_sdk_manager.send_to_property_inspector(self.sd_context, response)
        else:
            gl.sd_sdk_manager.send_to_plugin(self.plugin_uuid, response)

    def handle_show_alert(self) -> None:
        try:
            self.show_error(duration=2)
        except Warning:
            pass

    def handle_show_ok(self) -> None:
        try:
            self.show_overlay(_get_ok_image(), duration=2)
        except Warning:
            pass

    def handle_set_feedback(self, payload: dict) -> None:
        if not isinstance(payload, dict):
            return
        self.sd_feedback.update(payload)
        self.render()

    def handle_set_feedback_layout(self, payload: dict) -> None:
        layout = payload.get("layout")
        if layout and self.sd_action.encoder is not None:
            self.sd_action.encoder.layout = layout
        self.render()

    def handle_send_to_property_inspector(self, payload: dict) -> None:
        gl.sd_sdk_manager.send_to_property_inspector(self.sd_context, {
            "event": "sendToPropertyInspector",
            "action": self.sd_action.uuid,
            "context": self.sd_context,
            "payload": payload,
        })

    def handle_send_to_plugin(self, payload: dict) -> None:
        self._send("sendToPlugin", payload)

    # --------- #
    # Rendering #
    # --------- #

    def get_manifest_state(self):
        states = self.sd_action.states
        index = min(max(self.sd_state, 0), len(states) - 1)
        return states[index]

    def get_render_size(self) -> tuple[int, int]:
        try:
            size = self.get_input().get_image_size()
        except Exception:
            size = None
        return size or (REFERENCE_TILE_SIZE, REFERENCE_TILE_SIZE)

    def render(self) -> None:
        if not self.on_ready_called:
            return
        if not self.get_is_present():
            return

        manifest_state = self.get_manifest_state()
        size = self.get_render_size()

        image_spec = self.sd_image_overrides.get(self.sd_state) or manifest_state.image or self.sd_action.icon
        image = load_image(image_spec, self.plugin_path, size)

        if isinstance(self.input_ident, Input.Dial) and self.sd_feedback:
            image = _render_feedback(image, self.sd_feedback, size)

        try:
            self.set_media(image=image, update=False)
            self._render_labels(manifest_state)
            self.get_input().update()
        except Warning:
            # Raised when the action is not ready yet, nothing to render onto
            pass
        except Exception as e:
            log.error(f"Failed to render {self.sd_action.uuid}: {e}")

    def _render_labels(self, manifest_state) -> None:
        title = self.sd_title_overrides.get(self.sd_state)
        if title is None:
            title = manifest_state.title

        if not manifest_state.show_title:
            title = ""

        position = TITLE_ALIGNMENT_TO_POSITION.get(manifest_state.title_alignment, "center")
        color = parse_color(manifest_state.title_color)

        height = self.get_render_size()[1]
        font_size = round(manifest_state.font_size * height / REFERENCE_TILE_SIZE)

        font_style = None
        style = (manifest_state.font_style or "").lower()
        if "italic" in style:
            font_style = "italic"

        font_weight = 700 if "bold" in style else None

        for slot in ("top", "center", "bottom"):
            if slot == position:
                self.set_label(
                    title,
                    position=slot,
                    color=color,
                    font_family=manifest_state.font_family or None,
                    font_size=font_size,
                    font_weight=font_weight,
                    font_style=font_style,
                    update=False,
                )
            else:
                self.set_label("", position=slot, update=False)

    # ------------------ #
    # Property inspector #
    # ------------------ #

    def get_property_inspector_path(self) -> str | None:
        relative = self.sd_action.property_inspector_path or self.sd_plugin.sd_manifest.property_inspector_path
        if not relative:
            return None

        path = os.path.join(self.plugin_path, relative)
        return path if os.path.isfile(path) else None

    def get_custom_config_area(self):
        return gl.sd_sdk_manager.build_property_inspector(self)


def _get_ok_image(size: int = 144) -> Image.Image:
    """Draw the confirmation overlay shown by the SDK's showOk event."""
    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)

    margin = size // 8
    draw.ellipse((margin, margin, size - margin, size - margin), fill=(40, 170, 70, 230))

    width = max(2, size // 16)
    draw.line(
        [(size * 0.33, size * 0.52), (size * 0.45, size * 0.65), (size * 0.68, size * 0.37)],
        fill=(255, 255, 255, 255),
        width=width,
        joint="curve",
    )
    return image


def _render_feedback(background: Image.Image, feedback: dict, size: tuple[int, int]) -> Image.Image:
    """
    Draw the values a plugin sent through ``setFeedback`` onto the dial image.

    This covers the pieces of the Stream Deck+ layouts that carry information -
    an icon, a title, a value and a bar indicator - rather than reimplementing the
    full layout engine.
    """
    image = Image.new("RGBA", size, (0, 0, 0, 0))
    if background is not None:
        image.paste(background.resize(size, Image.Resampling.HAMMING), (0, 0))

    draw = ImageDraw.Draw(image)
    width, height = size

    def value_of(key: str):
        entry = feedback.get(key)
        if isinstance(entry, dict):
            return entry.get("value")
        return entry

    title = value_of("title")
    value = value_of("value")
    indicator = value_of("indicator")

    if title:
        draw.text((width / 2, height * 0.18), str(title), anchor="mm", fill=(255, 255, 255, 255))
    if value:
        draw.text((width / 2, height * 0.5), str(value), anchor="mm", fill=(255, 255, 255, 255))

    if isinstance(indicator, (int, float)):
        bar_height = max(3, height // 12)
        top = height - bar_height * 2
        draw.rectangle((width * 0.1, top, width * 0.9, top + bar_height), fill=(70, 70, 70, 255))
        filled = width * 0.1 + (width * 0.8) * max(0.0, min(1.0, indicator / 100))
        draw.rectangle((width * 0.1, top, filled, top + bar_height), fill=(255, 255, 255, 255))

    return image
