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

# Import own modules
from src.backend.PluginManager.ActionBase import ActionBase
from src.backend.PageManagement.Page import Page
from src.backend.DeckManagement.DeckController import DeckController

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

class ActionHolder:
    """
    Holder for ActionBase containing important information that can be used as long as the ActionBase is not initialized
    """
    def __init__(self, plugin_base: "PluginBase", action_base: ActionBase, action_id: str, action_name: str, icon: Gtk.Widget = None, min_app_version: str = None):
        
        ## Verify variables
        if action_id in ["", None]:
            raise ValueError("Please specify an action id")
        if action_name in ["", None]:
            raise ValueError("Please specify an action name")
        
        if icon is None:
            icon = Gtk.Image(icon_name="insert-image-symbolic")

        self.plugin_base = plugin_base
        self.action_base = action_base
        self.action_id = action_id
        self.action_name = action_name
        self.icon = icon
        self.min_app_version = min_app_version
        self.has_image_control = False
        self.has_top_label_control = False
        self.has_center_label_control = False
        self.has_bottom_label_control = False

    def get_is_compatible(self) -> bool:
        if self.min_app_version is not None:
            if version.parse(gl.app_version) < version.parse(self.min_app_version):
                return False
            
        return True

    def init_and_get_action(self, deck_controller: DeckController, page: Page, coords: str, state: int) -> ActionBase:
        if not self.get_is_compatible():
            return

        return self.action_base(
            action_id = self.action_id,
            action_name = self.action_name,
            deck_controller = deck_controller,
            page = page,
            coords = coords,
            plugin_base = self.plugin_base,
            state = state,
            has_image_control = self.has_image_control,
            has_top_label_control = self.has_top_label_control,
            has_center_label_control = self.has_center_label_control,
            has_bottom_label_control = self.has_bottom_label_control,
        )