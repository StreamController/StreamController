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

import globals as gl
from src.backend.DeckManagement.InputIdentifier import Input, InputIdentifier
from src.windows.mainWindow.elements.Sidebar.elements.ActionManager import ActionManager
from src.windows.mainWindow.elements.Sidebar.elements.BackgroundEditor import BackgroundEditor
from src.windows.mainWindow.elements.Sidebar.elements.IconSelector import IconSelector
from src.windows.mainWindow.elements.Sidebar.elements.ImageEditor import ImageEditor
from src.windows.mainWindow.elements.Sidebar.elements.LabelEditor import LabelEditor
from src.windows.mainWindow.elements.Sidebar.elements.StateSwitcher import StateSwitcher

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk
from loguru import logger as log

if TYPE_CHECKING:
    from src.windows.mainWindow.elements.Sidebar.Sidebar import Sidebar


class KeyEditor(Gtk.Box):
    def __init__(self, sidebar: "Sidebar", **kwargs):
        self.sidebar: "Sidebar" = sidebar
        super().__init__(**kwargs)
        self.set_orientation(Gtk.Orientation.VERTICAL)

        self.scrolled_window = Gtk.ScrolledWindow(hexpand=True, vexpand=True)
        self.append(self.scrolled_window)

        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, hexpand=True, vexpand=True)
        self.scrolled_window.set_child(self.main_box)

        self.state_switcher = StateSwitcher("keys", margin_start=20, margin_end=20, margin_top=10, margin_bottom=10, hexpand=True)
        self.state_switcher.add_switch_callback(self.on_state_switch)
        self.state_switcher.add_add_new_callback(self.on_add_new_state)
        self.state_switcher.set_n_states(0)
        self.main_box.append(self.state_switcher)

        self.icon_selector = IconSelector(sidebar, halign=Gtk.Align.CENTER, margin_top=30)
        self.main_box.append(self.icon_selector)

        self.image_editor = ImageEditor(sidebar, margin_top=90)
        self.main_box.append(self.image_editor)

        self.background_editor = BackgroundEditor(sidebar, margin_top=25)
        self.main_box.append(self.background_editor)

        self.label_editor = LabelEditor(sidebar, margin_top=25)
        self.main_box.append(self.label_editor)

        self.action_editor = ActionManager(sidebar, margin_top=25, width_request=400)
        self.main_box.append(self.action_editor)

        self.remove_state_button = Gtk.Button(label="Remove State", css_classes=["destructive-action"], margin_top=15, margin_bottom=15, margin_start=15, margin_end=15)
        self.remove_state_button.connect("clicked", self.on_remove_state)
        self.append(self.remove_state_button)

    def on_state_switch(self, *args):
        state = self.state_switcher.get_selected_state()

        controller = gl.app.main_win.get_active_controller()
        if controller is None:
            return
        
        controller_input = controller.get_input(self.sidebar.active_identifier)
        log.info(f"Going to state {state} from {controller_input.state}")
        controller_input.set_state(state=state, update_sidebar=True)

    def on_add_new_state(self, state):
        controller = gl.app.main_win.get_active_controller()
        if controller is None:
            return
        
        c_input = controller.get_input(self.sidebar.active_identifier)
        c_input.add_new_state()

        self.remove_state_button.set_visible(self.state_switcher.get_n_states() > 1)

    def on_remove_state(self, button):
        if self.state_switcher.get_n_states() <= 1:
            return

        controller = gl.app.main_win.get_active_controller()
        if controller is None:
            return
        
        active_state = self.state_switcher.get_selected_state()
        
        c_input = controller.get_input(self.sidebar.active_identifier)
        c_input.remove_state(active_state)

        self.remove_state_button.set_visible(self.state_switcher.get_n_states() > 1)

    def load_for_identifier(self, identifier: InputIdentifier, state: int):
        self.sidebar.active_identifier = identifier

        controller = gl.app.main_win.get_active_controller()
        if controller is None:
            return
        
        c_input = controller.get_input(identifier)

        self.state_switcher.load_for_identifier(identifier, state)
        c_input.set_state(state)

        self.remove_state_button.set_visible(self.state_switcher.get_n_states() > 1)

        self.icon_selector.load_for_identifier(identifier, state)
        self.image_editor.load_for_identifier(identifier, state)
        self.label_editor.load_for_identifier(identifier, state)
        self.action_editor.load_for_identifier(identifier, state)
        self.background_editor.load_for_identifier(identifier, state)


class KeyEditorKeyBox(Gtk.Box):
    def __init__(self, sidebar: "Sidebar", **kwargs):
        super().__init__(**kwargs)
        self.sidebar: "Sidebar" = sidebar

        self.scrolled_window = Gtk.ScrolledWindow(hexpand=True, vexpand=True)
        self.append(self.scrolled_window)

        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, hexpand=True, vexpand=True)
        self.scrolled_window.set_child(self.main_box)

        self.icon_selector = IconSelector(sidebar, halign=Gtk.Align.CENTER, margin_top=75)
        self.main_box.append(self.icon_selector)

        self.image_editor = ImageEditor(sidebar, margin_top=25)
        self.main_box.append(self.image_editor)

        self.background_editor = BackgroundEditor(sidebar, margin_top=25)
        self.main_box.append(self.background_editor)

        self.label_editor = LabelEditor(sidebar, margin_top=25)
        self.main_box.append(self.label_editor)

        self.action_editor = ActionManager(sidebar, margin_top=25, width_request=400)
        self.main_box.append(self.action_editor)

    def load_for_key(self, key: Input.Key, state: int):
        if not isinstance(key, Input.Key):
            raise TypeError("Input.Key expected")
        self.sidebar.active_identifier = key
        self.sidebar.active_state = state
        #TODO: Migrate to identifier
        self.icon_selector.load_for_identifier(key, state)
        self.image_editor.load_for_identifier(key.coords, state)
        self.label_editor.load_for_identifier(key, state)
        self.action_editor.load_for_coords(key.coords, state)
        self.background_editor.load_for_identifier(key, state)


class TestStack(Gtk.Stack):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.add_titled(Gtk.Label(), "key", "Key")
        self.add_titled(Gtk.Label(), "pages", "Pages")
