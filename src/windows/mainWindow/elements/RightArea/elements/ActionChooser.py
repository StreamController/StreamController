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
# Import gtk modules
import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw

# Import Python modules
from loguru import logger as log

# Import own modules
from src.backend.DeckManagement.HelperMethods import get_last_dir

# Import globals
import globals as gl

class ActionChooser(Gtk.Box):
    def __init__(self, right_area, **kwargs):
        super().__init__(hexpand=True, vexpand=True, **kwargs)
        self.right_area = right_area

        self.callback_function = None
        self.callback_args = None
        self.callback_kwargs = None

        self.build()

    def build(self):
        self.scrolled_window = Gtk.ScrolledWindow(hexpand=True, vexpand=True)
        self.append(self.scrolled_window)

        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, hexpand=True, vexpand=True, margin_top=4)
        self.scrolled_window.set_child(self.main_box)

        self.nav_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, hexpand=True)
        self.main_box.append(self.nav_box)

        self.back_button = Gtk.Button(icon_name="back")
        self.back_button.connect("clicked", self.on_back_button_click)
        self.nav_box.append(self.back_button)

        self.back_label = Gtk.Label(label="Go Back", margin_start=6, xalign=0, css_classes=["bold"])
        self.nav_box.append(self.back_label)

        self.header = Gtk.Label(label="Choose An Action", xalign=0, css_classes=["page-header"], margin_start=20, margin_top=30)
        self.main_box.append(self.header)

        self.plugin_group = PluginGroup(self, margin_top=40)
        self.main_box.append(self.plugin_group)

    def show(self, callback_function, current_stack_page, callback_args, callback_kwargs):
        # The current-stack_page is usefull in case the let_user_select_action is called by an plugin action in the action_configurator

        # Validate the callback function
        if not callable(callback_function):
            log.error(f"Invalid callback function: {callback_function}")
            self.callback_function = None
            self.callback_args = None
            self.callback_kwargs = None
            self.current_stack_page = None
            return
        
        self.callback_function = callback_function
        self.current_stack_page = current_stack_page
        self.callback_args = callback_args
        self.callback_kwargs = callback_kwargs

        self.right_area.set_visible_child(self)

    def on_back_button_click(self, button):
        self.right_area.set_visible_child_name("key_editor")

class PluginGroup(Adw.PreferencesGroup):
    def __init__(self, action_chooser, **kwargs):
        super().__init__(**kwargs)
        self.action_chooser = action_chooser

        self.build()

    def build(self):
        for plugin_name, plugin_dir in gl.plugin_manager.get_plugins().items():
            expander = PluginExpander(self, plugin_name, plugin_dir)
            self.add(expander)


class PluginExpander(Adw.ExpanderRow):
    def __init__(self, plugin_group, plugin_name, plugin_dir, **kwargs):
        super().__init__(**kwargs)
        self.plugin_group = plugin_group
        self.plugin_name = plugin_name
        self.plugin_dir = plugin_dir

        # Texts
        self.set_title(plugin_name)
        self.set_subtitle(get_last_dir(plugin_dir["folder-path"]))

        self.set_icon_name("view-paged")

        for action_name, action_class in plugin_dir["object"].ACTIONS.items():
            action_row = ActionRow(self, action_name, action_class)
            self.add_row(action_row)


class ActionRow(Adw.PreferencesRow):
    def __init__(self, expander, action_name, action_class, **kwargs):
        super().__init__(**kwargs)
        self.expander = expander
        self.action_name = action_name
        self.action_class = action_class

        self.button = Gtk.Button(hexpand=True, vexpand=True, overflow=Gtk.Overflow.HIDDEN,
                                 css_classes=["no-margin", "invisible"])
        self.button.connect("clicked", self.on_click)
        self.set_child(self.button)
        
        self.main_box = Gtk.Box(hexpand=True, vexpand=True, orientation=Gtk.Orientation.HORIZONTAL,
                                margin_top=10, margin_bottom=10)
        self.button.set_child(self.main_box)

        self.icon = Gtk.Image(icon_name="insert-image", icon_size=Gtk.IconSize.LARGE, margin_start=5)
        self.main_box.append(self.icon)

        self.label = Gtk.Label(label=self.action_name, margin_start=10, css_classes=["bold", "large-text"])
        self.main_box.append(self.label)

    def on_click(self, button):
        if self.action_class == None:
            return
        
        # Go back to old page
        self.expander.plugin_group.action_chooser.right_area.set_visible_child(self.expander.plugin_group.action_chooser.current_stack_page)

        # Verify the callback function
        if not callable(self.expander.plugin_group.action_chooser.callback_function):
            log.warning(f"Invalid callback function: {self.expander.plugin_group.action_chooser.callback_function}")
            return
        
        # Call the callback function
        callback = self.expander.plugin_group.action_chooser.callback_function
        args = self.expander.plugin_group.action_chooser.callback_args
        kwargs = self.expander.plugin_group.action_chooser.callback_kwargs

        
        callback(self.action_class, *args, **kwargs)

        # self.expander.plugin_group.action_chooser.callback_function(self.action_object, *self.expander.plugin_group.action_chooser.callback_args, **self.expander.plugin_group.action_chooser.callback_kwargs)
