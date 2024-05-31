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
from src.backend.PluginManager.ActionSupportTypes import ActionSupports
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
    def __init__(self, plugin_base: "PluginBase",
                 action_base: ActionBase,
                 action_id: str, action_name: str,
                 icon: Gtk.Widget = None,
                 min_app_version: str = None,
                 key_support: int = ActionSupports.Keys.UNTESTED,
                 touch_support: int = ActionSupports.Touch.UNTESTED,
                 dial_support: int = ActionSupports.Dials.UNTESTED
                 ):
        
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
        self.key_support = key_support
        self.touch_support = touch_support
        self.dial_support = dial_support

    def get_is_compatible(self) -> bool:
        if self.min_app_version is not None:
            if version.parse(gl.app_version) < version.parse(self.min_app_version):
                return False
            
        return True

    def init_and_get_action(self, deck_controller: DeckController, page: Page, state: int, type: str, identifier: str = None) -> ActionBase:
        if not self.get_is_compatible():
            return

        return self.action_base(
            action_id = self.action_id,
            action_name = self.action_name,
            deck_controller = deck_controller,
            page = page,
            type = type,
            identifier = identifier,
            plugin_base = self.plugin_base,
            state = state
        )
    
    def is_compatible_with_element(self, element: str) -> bool:
        if element == "key":
            return self.key_support > ActionSupports.Keys.NONE
        elif element == "touch":
            return self.touch_support > ActionSupports.Touch.NONE
        elif element == "dial":
            return self.dial_support > ActionSupports.Dials.NONE
        
    def is_untested_for_element(self, element: str) -> bool:
        if element == "key":
            return self.key_support == ActionSupports.Keys.UNTESTED
        elif element == "touch":
            return self.touch_support == ActionSupports.Touch.UNTESTED
        elif element == "dial":
            return self.dial_support == ActionSupports.Dials.UNTESTED