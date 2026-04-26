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
    def __init__(self, settings_page: "PageSettings", deck_serial_number, **kwargs):
        super().__init__()
        self.settings_page = settings_page
        self.deck_serial_number = deck_serial_number
        self.build()

        """
        To save performance and memory, we only load the thumbnail when the user sees the row
        """
        self.on_map_tasks: list = []
        self.connect("map", self.on_map)

        self.load_default()
        self.scale.connect("value-changed", self.on_value_changed)

    def on_map(self, widget):
        for f in self.on_map_tasks:
            f()
        self.on_map_tasks.clear()

    def build(self):
        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, hexpand=True,
                                margin_start=15, margin_end=15, margin_top=15, margin_bottom=15)
        self.set_child(self.main_box)

        self.label = Gtk.Label(label=gl.lm.get("deck.deck-group.brightness"), hexpand=True, xalign=0)
        self.main_box.append(self.label)

        self.scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, min=0, max=100, step=1)
        self.scale.set_draw_value(True)
        self.main_box.append(self.scale)

    def on_value_changed(self, scale):
        GLib.idle_add(self.on_value_changed_idle, scale)

    def on_value_changed_idle(self, scale):
        value = round(scale.get_value())

        # Update and save brightness in deck settings
        settings_manager = gl.settings_manager
        deck_settings = settings_manager.get_deck_settings(self.deck_serial_number)
        deck_settings.setdefault("brightness", {})["value"] = value
        settings_manager.save_deck_settings(self.deck_serial_number, deck_settings)

        # Check if brightness is overwritten by the current page
        page_dict = self.settings_page.deck_controller.active_page.dict
        overwrite = page_dict.get("settings", {}).get("brightness", {}).get("overwrite", False)

        # Apply brightness if not overwritten
        if not overwrite:
            self.settings_page.deck_controller.set_brightness(value)

    def load_default(self):
        if not self.get_mapped():
            self.on_map_tasks.clear()
            self.on_map_tasks.append(lambda: self.load_default())
            return
        
        original_values = gl.settings_manager.get_deck_settings(self.deck_serial_number)
        
        # Set defaut values 
        original_values.setdefault("brightness", {})
        brightness = original_values["brightness"].setdefault("value", 50)

        # Save if changed
        if original_values != gl.settings_manager.get_deck_settings(self.deck_serial_number):
            gl.settings_manager.save_deck_settings(self.deck_serial_number, original_values)

        # Update ui
        self.scale.set_value(brightness)
