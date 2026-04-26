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
from GtkHelper.GtkHelper import better_disconnect

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, GLib, Gtk


class Rotation(Adw.PreferencesRow):
    def __init__(self, settings_page: "PageSettings", deck_serial_number, **kwargs):
        super().__init__()
        self.settings_page = settings_page
        self.deck_serial_number = deck_serial_number
        self.build()

        self.load_default()
        self.connect("map", self.load_default)

    def build(self):
        self.main_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, hexpand=True,
                                margin_start=15, margin_end=15, margin_top=15, margin_bottom=15)
        self.set_child(self.main_box)

        self.rotation_label = Gtk.Label(label=gl.lm.get("deck.deck-group.rotation"), hexpand=True, xalign=0)
        self.main_box.append(self.rotation_label)

        self.toggle_group = Adw.ToggleGroup()
        self.main_box.append(self.toggle_group)

        self.toggle_0 = Adw.Toggle(label="0°", name="0")
        self.toggle_group.add(self.toggle_0)

        self.toggle_90 = Adw.Toggle(label="90°", name="90")
        self.toggle_group.add(self.toggle_90)

        self.toggle_180 = Adw.Toggle(label="180°", name="180")
        self.toggle_group.add(self.toggle_180)

        self.toggle_270 = Adw.Toggle(label="270°", name="270")
        self.toggle_group.add(self.toggle_270)


        self.toggle_group.connect("notify::active", self.on_value_changed)

    def on_value_changed(self, _, __):
        GLib.idle_add(self.on_value_changed_idle)

    def on_value_changed_idle(self):
        rot = int(self.toggle_group.get_active_name())

        deck_settings = gl.settings_manager.get_deck_settings(self.deck_serial_number)
        deck_settings["rotation"] = rot
        gl.settings_manager.save_deck_settings(self.deck_serial_number, deck_settings)

        self.settings_page.deck_controller.set_rotation(rot)

    def load_default(self, *args):
        better_disconnect(self.toggle_group, "notify::active")

        rot = gl.settings_manager.get_deck_settings(self.deck_serial_number).get("rotation", 0)
        self.toggle_group.set_active_name(str(rot))

        self.toggle_group.connect("notify::active", self.on_value_changed)
