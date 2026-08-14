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
from copy import deepcopy

# Import own modules
from src.backend.PluginManager.ActionBase import ActionBase
from src.backend.PluginManager.ActionInputSupport import ActionInputSupport
from src.backend.PluginManager.ActionCore import ActionCore
from src.backend.PageManagement.Page import Page
from src.backend.DeckManagement.DeckController import DeckController
from src.backend.DeckManagement.InputIdentifier import Input, InputIdentifier

# Import typing
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.backend.PluginManager.PluginBase import PluginBase

# Import gtk
import gi
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk

from packaging import version

import globals as gl

from loguru import logger as log

class ActionHolder:
    """
    Holder for ActionCore containing important information that can be used as long as the ActionCore is not initialized
    """
    def __init__(self,
        plugin_base: "PluginBase",
        action_name: str,
        action_core: ActionCore = None,
        action_base: ActionBase = None,
        icon: Gtk.Widget = None,
        min_app_version: str = None,
        action_id: str = None,
        action_id_suffix: str = None,
        action_support = {
            Input.Key: ActionInputSupport.UNTESTED,
            Input.Dial: ActionInputSupport.UNTESTED,
            Input.Touchscreen: ActionInputSupport.UNTESTED,
            Input.TouchKey: ActionInputSupport.UNTESTED,
            Input.Screen: ActionInputSupport.UNTESTED,
        },
        description: str = None,
        requirements: str = None,
        settings_schema: dict = None,
        *args, **kwargs):
        
        ## Verify variables
        if action_name in ["", None]:
            raise ValueError("Please specify an action name")
        if action_id in ["", None] and action_id_suffix in ["", None]:
            raise ValueError("Please specify an action id or an action id suffix")
        
        if icon is None:
            icon = Gtk.Image(icon_name="insert-image-symbolic")

        self.plugin_base = plugin_base
        self.action_core = action_core if action_core else action_base #backwards compatibility
        self.action_id_suffix = action_id_suffix
        self.action_id = action_id or f"{plugin_base.get_plugin_id()}::{action_id_suffix}"
        self.action_name = action_name
        self.icon = icon
        self.min_app_version = min_app_version
        self.action_support = deepcopy(action_support)

        # Optional self description, used by the AI assistant to configure this action
        # without a human picking every setting. All three are optional - an action that
        # does not fill them in simply shows up without documentation.
        self.description = description
        self.requirements = requirements
        self.settings_schema = deepcopy(settings_schema) if settings_schema else None

    def get_ai_documentation(self) -> str | None:
        """
        Renders what this action told us about itself, for the AI assistant's catalog.

        `settings_schema` maps a settings key to either a plain description string or a
        dict with any of "type", "description", "default", "example", "required",
        "values" - whichever the plugin author bothered to write down.

        Returns None when the action documented nothing.
        """
        if not any((self.description, self.requirements, self.settings_schema)):
            return None

        lines: list[str] = []

        if self.description:
            lines.append(f"      what it does: {self.description}")

        if self.requirements:
            lines.append(f"      requires: {self.requirements}")

        if self.settings_schema:
            lines.append("      settings:")
            for key, spec in self.settings_schema.items():
                if not isinstance(spec, dict):
                    lines.append(f'        "{key}": {spec}')
                    continue

                parts = []
                if spec.get("type"):
                    parts.append(str(spec["type"]))
                if spec.get("required"):
                    parts.append("required")
                if "default" in spec:
                    parts.append(f"default {spec['default']!r}")
                if spec.get("values"):
                    parts.append(f"one of {spec['values']}")
                if spec.get("example") is not None:
                    parts.append(f"e.g. {spec['example']!r}")

                detail = ", ".join(parts)
                description = spec.get("description", "")
                lines.append(f'        "{key}"' + (f" ({detail})" if detail else "")
                             + (f": {description}" if description else ""))

        return "\n".join(lines)

    def get_is_compatible(self) -> bool:
        if self.min_app_version is not None:
            if version.parse(gl.app_version) < version.parse(self.min_app_version):
                return False
            
        return True

    @log.catch
    def init_and_get_action(self, deck_controller: DeckController, page: Page, state: int, input_ident: InputIdentifier) -> ActionCore:
        if not self.get_is_compatible():
            return

        return self.action_core(
            action_id=self.action_id,
            action_name=self.action_name,
            deck_controller=deck_controller,
            page=page,
            input_ident=input_ident,
            plugin_base=self.plugin_base,
            state=state
        )
    
    def get_input_compatibility(self, identifier: InputIdentifier) -> ActionInputSupport:
        ident_type = type(identifier)
        if ident_type in self.action_support:
            return self.action_support[ident_type]
        # TouchKeys behave like regular keys
        if ident_type == Input.TouchKey and Input.Key in self.action_support:
            return self.action_support[Input.Key]
        # Neo Screen falls back to Key support since it renders images/labels like keys
        if ident_type == Input.Screen and Input.Key in self.action_support:
            return self.action_support[Input.Key]
        return ActionInputSupport.UNSUPPORTED