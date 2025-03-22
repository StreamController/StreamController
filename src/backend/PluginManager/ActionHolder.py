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
            Input.Touchscreen: ActionInputSupport.UNTESTED
        },
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
        return self.action_support.get(type(identifier), ActionInputSupport.UNSUPPORTED)