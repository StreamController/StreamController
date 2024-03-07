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

class BackgroundGroup(Adw.PreferencesGroup):
    def __init__(self, settings_page):
        super().__init__(title=gl.lm.get("deck.background-group.title"), description=gl.lm.get("deck.background-group.description"))
        self.deck_serial_number = settings_page.deck_serial_number
        self.media_row = BackgroundMediaRow(settings_page, self.deck_serial_number)
        self.add(self.media_row)


class BackgroundMediaRow(Adw.PreferencesRow):
    def __init__(self, settings_page, deck_serial_number, **kwargs):
        super().__init__()
        self.settings_page = settings_page
        self.deck_serial_number = deck_serial_number
        self.build()

    def build(self):
        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, hexpand=True,
                                margin_start=15, margin_end=15, margin_top=15, margin_bottom=15)
        self.set_child(self.main_box)

        self.enable_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, hexpand=True)
        self.main_box.append(self.enable_box)
        
        self.enable_label = Gtk.Label(label=gl.lm.get("deck.background-group.enable"), hexpand=True, xalign=0)
        self.enable_box.append(self.enable_label)

        self.enable_switch = Gtk.Switch()
        self.enable_box.append(self.enable_switch)

        self.config_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, hexpand=True, visible=False)
        self.main_box.append(self.config_box)

        self.config_box.append(Gtk.Separator(hexpand=True, margin_top=10, margin_bottom=10))

        self.media_selector = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, halign=Gtk.Align.CENTER)
        self.config_box.append(self.media_selector)

        self.media_selector_image = Gtk.Image() # Will be bound to the button by self.set_thumbnail()

        self.media_selector_button = Gtk.Button(label=gl.lm.get("deck.deck-group.media-select-label"), css_classes=["page-settings-media-selector"])
        self.media_selector.append(self.media_selector_button)

        self.connect_signals()
        self.load_defaults()

    def connect_signals(self):
        self.enable_switch.connect("state-set", self.on_toggle_enable)
        self.media_selector_button.connect("clicked", self.on_choose_image)

    def disconnect_signals(self):
        self.enable_switch.disconnect_by_func(self.on_toggle_enable)
        self.media_selector_button.disconnect_by_func(self.on_choose_image)


    def load_defaults(self):
        self.disconnect_signals()
        original_values = gl.settings_manager.get_deck_settings(self.deck_serial_number)

        # Set defaut values
        original_values.setdefault("background", {})
        path = original_values["background"].setdefault("path", "")
        enable = original_values["background"].setdefault("enable", False)
        loop = original_values["background"].setdefault("loop", False)
        fps = original_values["background"].setdefault("fps", 30)

        # Save if changed
        if original_values != gl.settings_manager.get_deck_settings(self.deck_serial_number):
            gl.settings_manager.save_deck_settings(self.deck_serial_number, original_values)

        # Update ui
        self.enable_switch.set_active(enable)
        self.config_box.set_visible(enable)
        self.set_thumbnail(path)

        self.connect_signals()

    def load_defaults_from_page(self):
        return
        if not hasattr(self.settings_page.deck_page.deck_controller, "active_page"):
            return
        if self.settings_page.deck_page.deck_controller.active_page == None:
            return
        
        original_values = None
        if "background" in self.settings_page.deck_page.deck_controller.active_page:
            original_values = self.settings_page.deck_page.deck_controller.active_page.dict["background"]

        overwrite = self.settings_page.deck_page.deck_controller.active_page.dict["background"].setdefault("overwrite", False)
        show = self.settings_page.deck_page.deck_controller.active_page.dict["background"].setdefault("show", False)
        file_path = self.settings_page.deck_page.deck_controller.active_page.dict["background"].setdefault("path", None)

        # Save if changed
        if original_values != self.settings_page.deck_page.deck_controller.active_page:
            self.settings_page.deck_page.deck_controller.active_page.save()

        self.overwrite_switch.set_active(overwrite)
        self.enable_switch.set_active(show)

        # Set config box state
        self.config_box.set_visible(overwrite)

        self.set_thumbnail(file_path)

    def on_toggle_enable(self, toggle_switch, state):
        config = gl.settings_manager.get_deck_settings(self.deck_serial_number)
        config["background"]["enable"] = state
        # Save
        gl.settings_manager.save_deck_settings(self.deck_serial_number, config)
        # Update
        self.config_box.set_visible(state)
        # Update
        self.settings_page.deck_controller.load_background(page=self.settings_page.deck_controller.active_page)

    def on_choose_image(self, button):
        settings = gl.settings_manager.get_deck_settings(self.deck_serial_number)
        settings.setdefault("background", {})
        media_path = settings["background"].setdefault("path", None)

        gl.app.let_user_select_asset(default_path=media_path, callback_func=self.update_image)

    def update_image(self, file_path):
        self.set_thumbnail(file_path)
        settings = gl.settings_manager.get_deck_settings(self.deck_serial_number)
        settings.setdefault("background", {})
        settings["background"]["path"] = file_path
        gl.settings_manager.save_deck_settings(self.deck_serial_number, settings)

        controller = self.settings_page.deck_controller
        controller.load_background(page=controller.active_page)

    def set_thumbnail(self, file_path):
        if file_path in [None, ""]:
            return
        # return
        image = gl.media_manager.get_thumbnail(file_path)
        pixbuf = image2pixbuf(image)
        self.media_selector_image.set_from_pixbuf(pixbuf)
        self.media_selector_button.set_child(self.media_selector_image)

    def set_deck_background(self, file_path):
        self.settings_page.deck_controller.set_background(file_path)