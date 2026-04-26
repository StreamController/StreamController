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
from typing import TYPE_CHECKING

import gi
from loguru import logger as log

import globals as gl
from GtkHelper.GtkHelper import BackButton
from src.backend.DeckManagement.InputIdentifier import InputIdentifier
from src.windows.mainWindow.elements.Sidebar.elements.ActionChooserParts.Expanders import (
    ActionChooserExpander,
    ActionGroupExpander,
    PluginExpander,
)
from src.windows.mainWindow.elements.Sidebar.elements.ActionChooserParts.OpenStoreButton import (
    OpenStoreButton,
)
from src.windows.mainWindow.elements.Sidebar.elements.ActionChooserParts.PluginActionRow import (
    PluginActionRow,
)
from src.windows.mainWindow.elements.Sidebar.elements.ActionChooserParts.PluginGroup import (
    PluginGroup,
)

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk

if TYPE_CHECKING:
    from src.windows.mainWindow.elements.Sidebar import Sidebar

__all__ = [
    "ActionChooser",
    "ActionChooserExpander",
    "ActionGroupExpander",
    "OpenStoreButton",
    "PluginActionRow",
    "PluginExpander",
    "PluginGroup",
]


class ActionChooser(Gtk.Box):
    def __init__(self, sidebar: "Sidebar", **kwargs):
        super().__init__(hexpand=True, vexpand=True, **kwargs)
        self.sidebar: "Sidebar" = sidebar

        self.callback_function = None
        self.callback_args = None
        self.callback_kwargs = None
        self.identifier: InputIdentifier = None

        self.build()

    def build(self):
        self.scrolled_window = Gtk.ScrolledWindow(hexpand=True, vexpand=True)
        self.append(self.scrolled_window)

        self.clamp = Adw.Clamp()
        self.scrolled_window.set_child(self.clamp)

        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, hexpand=True, vexpand=True, margin_top=4)
        self.clamp.set_child(self.main_box)

        self.nav_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, hexpand=True)
        self.main_box.append(self.nav_box)

        self.back_button = BackButton()
        self.back_button.connect("clicked", self.on_back_button_click)
        self.nav_box.append(self.back_button)

        self.header = Gtk.Label(label=gl.lm.get("action-chooser.header"), xalign=0, css_classes=["page-header"], margin_top=30)
        self.main_box.append(self.header)

        self.search_entry = Gtk.SearchEntry(margin_top=10,
                                            placeholder_text=gl.lm.get("action-chooser.search-entry.placeholder"),
                                            hexpand=True)
        self.search_entry.connect("search-changed", self.on_search_changed)
        self.main_box.append(self.search_entry)

        self.plugin_group = PluginGroup(self, margin_top=40)
        self.main_box.append(self.plugin_group)

        self.open_store_button = OpenStoreButton(margin_top=40, margin_bottom=40)
        self.main_box.append(self.open_store_button)

    def show(self, callback_function, current_stack_page, identifier: InputIdentifier, callback_args, callback_kwargs):
        # The current-stack_page is usefull in case the let_user_select_action is called by an plugin action in the action_configurator

        # Validate the callback function
        if not callable(callback_function):
            log.error(f"Invalid callback function: {callback_function}")
            self.callback_function = None
            self.callback_args = None
            self.callback_kwargs = None
            self.current_stack_page = None
            self.identifier = None
            return
        
        self.callback_function = callback_function
        self.current_stack_page = current_stack_page
        self.callback_args = callback_args
        self.callback_kwargs = callback_kwargs
        self.identifier = identifier
        self.plugin_group.set_identifier(identifier)

        self.sidebar.main_stack.set_visible_child(self)

    def on_back_button_click(self, button):
        self.sidebar.main_stack.set_visible_child_name("configurator_stack")

    def on_search_changed(self, search_entry):
        self.plugin_group.search()
