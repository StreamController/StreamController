"""
Author: Core447
Year: 2024

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
from gi.repository import Gtk, Adw, GLib

# Import Python modules
import cv2
import threading
from loguru import logger as log
from math import floor
from time import sleep

# Import globals
import globals as gl

# Import own modules
from src.backend.DeckManagement.ImageHelpers import image2pixbuf, is_transparent

class FakeDeckGroup(Adw.PreferencesGroup):
    def __init__(self, settings_page):
        super().__init__(title=gl.lm.get("deck.fake-deck-group.title"), description=gl.lm.get("deck.fake-deck-group.description"))
        self.set_margin_top(50)
        self.deck_serial_number = settings_page.deck_serial_number

        self.layout = Layout(settings_page)

        self.add(self.layout)

class Layout(Adw.PreferencesRow):
    def __init__(self, settings_page: "PageSettings", **kwargs):
        super().__init__()
        self.settings_page = settings_page
        self.build()

    def build(self):
        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, hexpand=True,
                                margin_start=15, margin_end=15, margin_top=15, margin_bottom=15)
        self.set_child(self.main_box)

        self.rows_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, hexpand=True)
        self.main_box.append(self.rows_box)

        self.rows_label = Gtk.Label(label=gl.lm.get("deck.fake-deck-group.layout.columns.label"), xalign=0, hexpand=True)
        self.rows_box.append(self.rows_label)

        self.rows_spinner = Gtk.SpinButton.new_with_range(1, 50, 1)
        self.rows_box.append(self.rows_spinner)

        self.columns_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, hexpand=True, margin_top=15)
        self.main_box.append(self.columns_box)

        self.columns_label = Gtk.Label(label=gl.lm.get("deck.fake-deck-group.layout.rows.label"), xalign=0, hexpand=True)
        self.columns_box.append(self.columns_label)

        self.columns_spinner = Gtk.SpinButton.new_with_range(1, 50, 1)
        self.columns_box.append(self.columns_spinner)

        self.load_defaults()

        self.columns_spinner.connect("value-changed", self.on_change_columns)
        self.rows_spinner.connect("value-changed", self.on_change_rows)

    def load_defaults(self):
        deck = self.settings_page.deck_controller.deck
        self.rows_spinner.set_value(deck.key_layout()[0])
        self.columns_spinner.set_value(deck.key_layout()[1])

    def on_change_rows(self, widget):
        rows = self.rows_spinner.get_value_as_int()

        deck = self.settings_page.deck_controller.deck

        deck.set_key_layout([rows, deck.key_layout()[1]])

        self.settings_page.deck_controller.init_keys()

        grid = self.settings_page.deck_stack_child.page_settings.grid_page
        grid.regenerate_buttons()
        grid.build()

    def on_change_columns(self, widget):
        columns = self.columns_spinner.get_value_as_int()

        deck = self.settings_page.deck_controller.deck

        deck.set_key_layout([deck.key_layout()[0], columns])

        self.settings_page.deck_controller.init_keys()

        grid = self.settings_page.deck_stack_child.page_settings.grid_page
        grid.regenerate_buttons()
        grid.build()