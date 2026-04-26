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

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, GLib, Gtk


class Brightness(Adw.PreferencesRow):
    def __init__(self, page_editor: "PageEditor", **kwargs):
        super().__init__()
        self.page_editor = page_editor

        """
        To save performance and memory, we only load the thumbnail when the user sees the row
        """
        self.on_map_tasks: list = []
        self.connect("map", self.on_map)

        self.build()

    def on_map(self, widget):
        for f in self.on_map_tasks:
            f()
        self.on_map_tasks.clear()

    def build(self):
        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, hexpand=True,
                                margin_start=15, margin_end=15, margin_top=15, margin_bottom=15)
        self.set_child(self.main_box)

        self.overwrite_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, hexpand=True)
        self.main_box.append(self.overwrite_box)

        self.overwrite_label = Gtk.Label(label=gl.lm.get("page-settings-overwrite-brightness"), hexpand=True, xalign=0)
        self.overwrite_box.append(self.overwrite_label)

        self.overwrite_switch = Gtk.Switch()
        self.overwrite_box.append(self.overwrite_switch)

        self.config_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, visible=False)
        self.main_box.append(self.config_box)

        self.config_box.append(Gtk.Separator(hexpand=True, margin_top=10, margin_bottom=10))

        self.label = Gtk.Label(label=gl.lm.get("brightness"), hexpand=True, xalign=0)
        self.config_box.append(self.label)

        self.scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, min=0, max=100, step=1)
        self.scale.set_draw_value(True)
        # self.set_scale_initial_value()
        self.config_box.append(self.scale)

        # Load from config
        self.load_defaults_from_page()

        self.overwrite_switch.connect("state-set", self.on_toggle_overwrite)
        self.scale.connect("value-changed", self.on_value_changed)

    def set_scale_initial_value(self):
        self.load_defaults_from_page()

    def set_scale_from_page(self, page):
        if page == None:
            self.scale.set_sensitive(False)
            self.main_box.append(Gtk.Label(label="Error", hexpand=True, xalign=0, css_classes=["red-color"]))
            return

        brightness = page.dict.get("brightness", {}).get("value", 75)
        self.scale.set_value(brightness)

    def on_value_changed(self, scale):
        GLib.idle_add(self.on_value_changed_idle, scale)

    def on_value_changed_idle(self, scale):
        value = round(scale.get_value())
        # update value in page
        page_dict = self.page_editor.get_page_data()
        page_dict.setdefault("brightness", {})
        page_dict["brightness"]["value"] = value
        self.page_editor.set_page_data(page_dict, reload_brightness=True, reload_screensaver=False, reload_background=False, reload_inputs=False)

    def on_toggle_overwrite(self, toggle_switch, state):
        self.config_box.set_visible(state)

        deck_controller = self.page_editor.deck_page.deck_controller
        # Update page
        page_dict = self.page_editor.get_page_data()
        page_dict.setdefault("brightness", {})
        page_dict["brightness"]["overwrite"] = state
        self.page_editor.set_page_data(page_dict, reload_brightness=True, reload_screensaver=False, reload_background=False, reload_inputs=False)

    def load_defaults_from_page(self):
        if not self.get_mapped():
            self.on_map_tasks.clear()
            self.on_map_tasks.append(lambda: self.load_defaults_from_page())

        # Update ui
        page_dict = self.page_editor.get_page_data()
        active = page_dict.get("brightness", {}).get("overwrite", False)
        self.overwrite_switch.set_active(active)
        self.config_box.set_visible(active)
