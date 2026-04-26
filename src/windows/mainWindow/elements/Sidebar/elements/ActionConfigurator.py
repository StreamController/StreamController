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
import gi

import globals as gl
from GtkHelper.GtkHelper import BackButton
from src.windows.mainWindow.elements.Sidebar.elements.ActionConfiguratorParts.CommentGroup import (
    CommentGroup,
)
from src.windows.mainWindow.elements.Sidebar.elements.ActionConfiguratorParts.ConfigGroup import (
    ConfigGroup,
)
from src.windows.mainWindow.elements.Sidebar.elements.ActionConfiguratorParts.CustomConfigs import (
    CustomConfigs,
)
from src.windows.mainWindow.elements.Sidebar.elements.ActionConfiguratorParts.EventAssigner import (
    EventAssignerRow,
    EventAssignerRowItem,
    EventAssignerUI,
)
from src.windows.mainWindow.elements.Sidebar.elements.ActionConfiguratorParts.RemoveButton import (
    RemoveButton,
)

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk

__all__ = [
    "ActionConfigurator",
    "CommentGroup",
    "ConfigGroup",
    "CustomConfigs",
    "EventAssignerRow",
    "EventAssignerRowItem",
    "EventAssignerUI",
    "RemoveButton",
]


class ActionConfigurator(Gtk.Box):
    def __init__(self, sidebar, **kwargs):
        super().__init__(**kwargs)
        self.sidebar = sidebar
        self.build()

    def build(self):
        self.scrolled_window = Gtk.ScrolledWindow(hexpand=True, vexpand=True, margin_end=4)
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

        self.header = Gtk.Label(label=gl.lm.get("action-configurator-header"), xalign=0, css_classes=["page-header"], margin_start=20, margin_top=30)
        self.main_box.append(self.header)

        self.comment_group = CommentGroup(self, margin_top=20)
        self.main_box.append(self.comment_group)

        self.event_assigner = EventAssignerUI(self, margin_top=20)
        self.main_box.append(self.event_assigner)

        self.main_box.append(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL, margin_top=20, margin_bottom=20))

        self.config_group = ConfigGroup(self)
        self.main_box.append(self.config_group)

        self.config_group_and_custom_configs_separator = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL, margin_top=20, margin_bottom=20)
        self.main_box.append(self.config_group_and_custom_configs_separator)

        self.custom_configs = CustomConfigs(self, margin_top=6)
        self.main_box.append(self.custom_configs)

        self.remove_button = RemoveButton(self, margin_top=12)
        self.main_box.append(self.remove_button)

    def load_for_action(self, action, index):
        self.config_group.load_for_action(action)
        self.custom_configs.load_for_action(action)
        self.remove_button.load_for_action(action, index)
        self.comment_group.load_for_action(action, index)
        self.event_assigner.load_for_action(action)

        self.config_group_and_custom_configs_separator.set_visible(self.config_group.is_visible() and self.custom_configs.is_visible())

    def on_back_button_click(self, button):
        self.sidebar.main_stack.set_visible_child_name("configurator_stack")
