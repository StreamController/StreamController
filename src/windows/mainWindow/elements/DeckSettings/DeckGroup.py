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
import os
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

class DeckGroup(Adw.PreferencesGroup):
    def __init__(self, settings_page):
        super().__init__(title=gl.lm.get("deck.deck-group.title"), description=gl.lm.get("deck.deck-group.description"))
        self.deck_serial_number = settings_page.deck_serial_number

        self.brightness = Brightness(settings_page, self.deck_serial_number)
        self.screensaver = Screensaver(settings_page, self.deck_serial_number)

        self.add(self.brightness)
        self.add(self.screensaver)

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
        # update value in deck settings
        deck_settings = gl.settings_manager.get_deck_settings(self.deck_serial_number)
        deck_settings.setdefault("brightness", {})
        deck_settings["brightness"]["value"] = value
        # save settings
        gl.settings_manager.save_deck_settings(self.deck_serial_number, deck_settings)
        # update brightness if current page does not overwrite
        overwrite = False
        if "brightness" in self.settings_page.deck_controller.active_page.dict:
            if "overwrite" in self.settings_page.deck_controller.active_page.dict["brightness"]:
                overwrite = self.settings_page.deck_controller.active_page.dict["brightness"]["overwrite"]
        if overwrite == False:
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

class Screensaver(Adw.PreferencesRow):
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

        self.load_defaults()

    def on_map(self, widget):
        for f in self.on_map_tasks:
            f()
        self.on_map_tasks.clear()
    
    def build(self):
        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, hexpand=True,
                                margin_start=15, margin_end=15, margin_top=15, margin_bottom=15)
        self.set_child(self.main_box)

        self.enable_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, hexpand=True)
        self.main_box.append(self.enable_box)

        self.enable_label = Gtk.Label(label=gl.lm.get("deck.deck-group.enable-screensaver"), hexpand=True, xalign=0)
        self.enable_box.append(self.enable_label)

        self.enable_switch = Gtk.Switch()
        self.enable_box.append(self.enable_switch)

        self.config_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, hexpand=True, visible=False)
        self.main_box.append(self.config_box)

        self.config_box.append(Gtk.Separator(hexpand=True, margin_top=10, margin_bottom=10))

        self.time_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, hexpand=True)
        self.config_box.append(self.time_box)

        self.time_label = Gtk.Label(label=gl.lm.get("screensaver-delay"), hexpand=True, xalign=0)
        self.time_box.append(self.time_label)

        self.time_spinner = Gtk.SpinButton.new_with_range(1, 60, 1)
        self.time_box.append(self.time_spinner)

        self.media_selector_label = Gtk.Label(label=gl.lm.get("deck.deck-group.media-to-show"), hexpand=True, xalign=0)
        self.config_box.append(self.media_selector_label)

        self.media_selector_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, halign=Gtk.Align.CENTER)
        self.config_box.append(self.media_selector_box)

        self.media_selector_button = Gtk.Button(label=gl.lm.get("deck.deck-group.media-select-label"), css_classes=["page-settings-media-selector"])
        self.media_selector_box.append(self.media_selector_button)

        self.progress_bar = Gtk.ProgressBar(hexpand=True, margin_top=10, text=gl.lm.get("background.processing"), fraction=0, show_text=True, visible=False)
        self.config_box.append(self.progress_bar)

        self.media_selector_image = Gtk.Image() # Will be bound to the button by self.set_thumbnail()

        self.loop_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, hexpand=True, margin_bottom=15)
        self.config_box.append(self.loop_box)

        self.loop_label = Gtk.Label(label=gl.lm.get("deck.deck-group.media-loop"), hexpand=True, xalign=0)
        self.loop_box.append(self.loop_label)

        self.loop_switch = Gtk.Switch()
        self.loop_box.append(self.loop_switch)

        self.fps_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, hexpand=True)
        self.config_box.append(self.fps_box)

        self.fps_label = Gtk.Label(label=gl.lm.get("deck.deck-group.media-fps"), hexpand=True, xalign=0)
        self.fps_box.append(self.fps_label)

        self.fps_spinner = Gtk.SpinButton.new_with_range(1, 30, 1)
        self.fps_box.append(self.fps_spinner)

        self.brightness_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, hexpand=True)
        self.config_box.append(self.brightness_box)

        self.brightness_label = Gtk.Label(label=gl.lm.get("deck.deck-group.brightness"), hexpand=True, xalign=0)
        self.brightness_box.append(self.brightness_label)

        self.scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, min=0, max=100, step=1)
        self.brightness_box.append(self.scale)

        self.connect_signals()

    def connect_signals(self) -> None:
        self.enable_switch.connect("state-set", self.on_toggle_enable)
        self.time_spinner.connect("value-changed", self.on_change_time)
        self.media_selector_button.connect("clicked", self.on_choose_image)
        self.loop_switch.connect("state-set", self.on_toggle_loop)
        self.fps_spinner.connect("value-changed", self.on_change_fps)
        self.scale.connect("value-changed", self.on_change_brightness)

    def disconnect_signals(self) -> None:
        self.enable_switch.disconnect_by_func(self.on_toggle_enable)
        self.time_spinner.disconnect_by_func(self.on_change_time)
        self.media_selector_button.disconnect_by_func(self.on_choose_image)
        self.loop_switch.disconnect_by_func(self.on_toggle_loop)
        self.fps_spinner.disconnect_by_func(self.on_change_fps)
        self.scale.disconnect_by_func(self.on_change_brightness)



    def load_defaults(self):
        self.disconnect_signals()
        original_values = gl.settings_manager.get_deck_settings(self.deck_serial_number)
        
        # Set defaut values 
        original_values.setdefault("screensaver", {})
        enable = original_values["screensaver"].setdefault("enable", False)
        path = original_values["screensaver"].setdefault("path", None)
        loop = original_values["screensaver"].setdefault("loop", False)
        fps = original_values["screensaver"].setdefault("fps", 30)
        time = original_values["screensaver"].setdefault("time-delay", 5)
        brightness = original_values["screensaver"].setdefault("brightness", 30)

        # Save if changed
        if original_values != gl.settings_manager.get_deck_settings(self.deck_serial_number):
            gl.settings_manager.save_deck_settings(self.deck_serial_number, original_values)

        # Update ui
        self.enable_switch.set_active(enable)
        self.config_box.set_visible(enable)
        self.time_spinner.set_value(time)
        self.loop_switch.set_active(loop)
        self.fps_spinner.set_value(fps)
        self.scale.set_value(brightness)

        if path is not None:
            if os.path.isfile(path):
                self.set_thumbnail(path)

        self.connect_signals()


    def on_toggle_enable(self, toggle_switch, state):
        config = gl.settings_manager.get_deck_settings(self.deck_serial_number)
        config["screensaver"]["enable"] = state
        # Save
        gl.settings_manager.save_deck_settings(self.deck_serial_number, config)
        # Update enable if not overwritten by the active page
        active_page = self.settings_page.deck_controller.active_page
        if not active_page.dict["screensaver"]["overwrite"]:
            self.settings_page.deck_controller.screen_saver.set_enable(state)

        self.config_box.set_visible(state)

    def on_toggle_loop(self, toggle_switch, state):
        config = gl.settings_manager.get_deck_settings(self.deck_serial_number)
        config["screensaver"]["loop"] = state
        # Save
        gl.settings_manager.save_deck_settings(self.deck_serial_number, config)

        # Update loop if not overwritten by the active page
        active_page = self.settings_page.deck_controller.active_page
        if not active_page.dict["screensaver"]["overwrite"]:
            self.settings_page.deck_controller.screen_saver.set_loop(state)

    def on_change_fps(self, spinner):
        config = gl.settings_manager.get_deck_settings(self.deck_serial_number)
        config["screensaver"]["fps"] = spinner.get_value_as_int()
        # Save
        gl.settings_manager.save_deck_settings(self.deck_serial_number, config)
        # Update fps if not overwritten by the active page
        active_page = self.settings_page.deck_controller.active_page
        if not active_page.dict["screensaver"]["overwrite"]:
            self.settings_page.deck_controller.screen_saver.set_fps(spinner.get_value_as_int())

    def on_change_time(self, spinner):
        config = gl.settings_manager.get_deck_settings(self.deck_serial_number)
        config["screensaver"]["time-delay"] = round(spinner.get_value_as_int())
        # Save
        gl.settings_manager.save_deck_settings(self.deck_serial_number, config)
        # Update time if not overwritten by the active page
        active_page = self.settings_page.deck_controller.active_page
        if not active_page.dict["screensaver"]["overwrite"]:
            self.settings_page.deck_controller.screen_saver.set_time(round(spinner.get_value_as_int()))

    def on_change_brightness(self, scale):
        config = gl.settings_manager.get_deck_settings(self.deck_serial_number)
        config["screensaver"]["brightness"] = scale.get_value()
        # Save
        gl.settings_manager.save_deck_settings(self.deck_serial_number, config)
        # Update brightness if not overwritten by the active page
        active_page = self.settings_page.deck_controller.active_page
        if not active_page.dict["screensaver"]["overwrite"]:
            self.settings_page.deck_controller.screen_saver.set_brightness(scale.get_value())

    def set_thumbnail(self, file_path):
        if file_path == None:
            return
        if not os.path.isfile(file_path):
            return
        image = gl.media_manager.get_thumbnail(file_path)
        pixbuf = image2pixbuf(image)
        self.media_selector_image.pixbuf = None
        del self.media_selector_image.pixbuf
        self.media_selector_image.set_from_pixbuf(pixbuf)
        self.media_selector_button.set_child(self.media_selector_image)

    def on_choose_image(self, button):
        settings = gl.settings_manager.get_deck_settings(self.deck_serial_number)
        settings.setdefault("screensaver", {})
        media_path = settings["screensaver"].get("path", None)

        gl.app.let_user_select_asset(default_path=media_path, callback_func=self.update_image)

    def update_image(self, image_path):
        self.set_thumbnail(image_path)
        settings = gl.settings_manager.get_deck_settings(self.deck_serial_number)
        settings.setdefault("screensaver", {})
        settings["screensaver"]["path"] = image_path
        gl.settings_manager.save_deck_settings(self.deck_serial_number, settings)

        deck_controller = self.settings_page.deck_controller
        deck_controller.load_screensaver(deck_controller.active_page)