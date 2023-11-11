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

class ActionConfigurator(Gtk.Box):
    def __init__(self, right_area, **kwargs):
        super().__init__(**kwargs)
        self.right_area = right_area
        self.build()

    def build(self):
        self.scrolled_window = Gtk.ScrolledWindow(hexpand=True, vexpand=True, margin_end=4)
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

        self.header = Gtk.Label(label="Configure Action", xalign=0, css_classes=["page-header"], margin_start=20, margin_top=30)
        self.main_box.append(self.header)

        self.config_group = ConfigGroup(self, margin_top=40)
        self.main_box.append(self.config_group)

        self.custom_configs = CustomConfigs(self, margin_top=6)
        self.main_box.append(self.custom_configs)

        self.remove_button = RemoveButton(self, margin_top=12)
        self.main_box.append(self.remove_button)

    def load_for_action(self, action, index):
        self.config_group.load_for_action(action)
        self.custom_configs.load_for_action(action)
        self.remove_button.load_for_action(action, index)

    def on_back_button_click(self, button):
        self.right_area.set_visible_child_name("key_editor")

class ConfigGroup(Adw.PreferencesGroup):
    def __init__(self, parent, **kwargs):
        super().__init__(**kwargs)
        self.parent = parent
        self.loaded_rows = []
        self.build()

    def build(self):
        pass

    def load_for_action(self, action):
        if not hasattr(action, "get_config_rows"):
            self.hide()
            return
        if action.get_config_rows() is None:
            self.hide()
            return
        # Load labels
        self.set_title(action.ACTION_NAME)
        self.set_description(action.PLUGIN_BASE.PLUGIN_NAME)

        # Clear
        self.clear()

        # Load rows
        rows = action.get_config_rows()
        for row in rows:
            self.add(row)
            self.loaded_rows.append(row)
        
        # Show
        self.show()

    def clear(self):
        for row in self.loaded_rows:
            self.remove(row)
        self.loaded_rows = []

class CustomConfigs(Gtk.Box):
    def __init__(self, parent, **kwargs):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, **kwargs)
        self.parent = parent

        self.append(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL, margin_bottom=6))

        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, hexpand=True)
        self.append(self.main_box)

    def load_for_action(self, action):
        if not hasattr(action, "get_custom_config_area"):
            self.hide()
            return
        
        if action.get_custom_config_area() is None:
            self.hide()
            return
        
        # Clear
        self.clear()

        # Append custom config area
        custom_config_area = action.get_custom_config_area()
        if custom_config_area is not None:
            self.main_box.append(custom_config_area)

        # Show
        self.show()

    def clear(self):
        while self.main_box.get_first_child() is not None:
            self.main_box.remove(self.main_box.get_first_child())

class RemoveButton(Gtk.Button):
    def __init__(self, configurator, **kwargs):
        super().__init__(**kwargs)
        self.set_css_classes(["remove-action-button"])
        self.configurator = configurator
        self.set_label("Remove Action")
        self.connect("clicked", self.on_remove_button_click)

        self.action = None
        self.index = None

    def on_remove_button_click(self, button):
        controller = self.configurator.right_area.main_window.leftArea.deck_stack.get_visible_child().deck_controller
        page = controller.active_page

        # Swtich to main editor page
        self.configurator.right_area.set_visible_child_name("key_editor")

        # Remove from action_objects
        del page.action_objects[self.action.page_coords][self.index]

        # Remove from page json
        page["keys"][self.action.page_coords]["actions"].pop(self.index)
        page.save()

        # Reload configurator
        self.configurator.right_area.load_for_coords(self.action.page_coords.split("x"))

        # Check whether we have to reload the key
        load = not page.has_key_an_image_controlling_action(self.action.page_coords)
        if load:
            controller.load_key(self.action.page_coords)

        # Destroy the actual action
        del self.action

    def load_for_action(self, action, index):
        self.action = action
        self.index = index