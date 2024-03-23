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
from copy import copy

# Import globals
import globals as gl

# Import own modules
from src.backend.DeckManagement.ImageHelpers import image2pixbuf, is_transparent

class DeckGroup(Adw.PreferencesGroup):
    def __init__(self, settings_page):
        super().__init__(title=gl.lm.get("page-settings-deck-heading"), description=gl.lm.get("page-settings-only-current-page-hint"))

        self.brightness = Brightness(settings_page)
        self.screensaver = Screensaver(settings_page)

        self.add(self.brightness)
        self.add(self.screensaver)

class Brightness(Adw.PreferencesRow):
    def __init__(self, settings_page: "PageSettings", **kwargs):
        super().__init__()
        self.settings_page = settings_page
        self.build()

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
        # Load default scalar value
        current_page = None
        if hasattr(self.settings_page.deck_page.deck_controller, "active_page"):
            current_page = self.settings_page.deck_page.deck_controller.active_page

        self.load_defaults_from_page()

    def set_scale_from_page(self, page):
        if page == None:
            self.scale.set_sensitive(False)
            self.main_box.append(Gtk.Label(label="Error", hexpand=True, xalign=0, css_classes=["red-color"]))
            return

        brightness = page.dict.get("brightness", {}).get("value", 75)
        self.scale.set_value(brightness)

    def on_value_changed(self, scale):
        value = round(scale.get_value())
        # update value in page
        self.settings_page.deck_page.deck_controller.active_page.dict.setdefault("brightness", {})
        self.settings_page.deck_page.deck_controller.active_page.dict["brightness"]["value"] = value
        self.settings_page.deck_page.deck_controller.active_page.save()
        # update deck without reload of page
        self.settings_page.deck_page.deck_controller.set_brightness(value)

    def on_toggle_overwrite(self, toggle_switch, state):
        self.config_box.set_visible(state)

        deck_controller = self.settings_page.deck_page.deck_controller
        # Update page
        deck_controller.active_page.dict.setdefault("brightness", {})
        deck_controller.active_page.dict["brightness"]["overwrite"] = state
        # Save
        deck_controller.active_page.save()
        # Reload
        deck_controller.load_page(deck_controller.active_page, load_screensaver=False, load_background=False, load_keys=False)

    def load_defaults_from_page(self):
        # Verify if page exists
        if not hasattr(self.settings_page.deck_page.deck_controller, "active_page"):
            return
        if self.settings_page.deck_page.deck_controller.active_page == None:
            return

        original_values = copy(self.settings_page.deck_page.deck_controller.active_page.dict)
        
        # Set defaut values 
        self.settings_page.deck_page.deck_controller.active_page.dict.setdefault("brightness", {})
        self.settings_page.deck_page.deck_controller.active_page.dict["brightness"].setdefault("value", 50)
        self.settings_page.deck_page.deck_controller.active_page.dict["brightness"].setdefault("overwrite", False)

        # Save if changed
        if original_values != self.settings_page.deck_page.deck_controller.active_page.dict:
            self.settings_page.deck_page.deck_controller.active_page.save()

        # Update ui
        self.set_scale_from_page(self.settings_page.deck_page.deck_controller.active_page)
        active = self.settings_page.deck_page.deck_controller.active_page.dict["brightness"]["overwrite"]
        self.overwrite_switch.set_active(active)
        self.config_box.set_visible(active)

class Screensaver(Adw.PreferencesRow):
    def __init__(self, settings_page: "PageSettings", **kwargs):
        super().__init__(css_classes=["no-click"])
        self.settings_page = settings_page
        self.build()
    
    def build(self):
        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, hexpand=True,
                                margin_start=15, margin_end=15, margin_top=15, margin_bottom=15)
        self.set_child(self.main_box)

        self.overwrite_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, hexpand=True)
        self.main_box.append(self.overwrite_box)

        self.overwrite_label = Gtk.Label(label=gl.lm.get("page-settings-overwrite-screensaver"), hexpand=True, xalign=0)
        self.overwrite_box.append(self.overwrite_label)

        self.overwrite_switch = Gtk.Switch()
        self.overwrite_box.append(self.overwrite_switch)

        self.config_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, hexpand=True, visible=False)
        self.main_box.append(self.config_box)

        self.config_box.append(Gtk.Separator(margin_top=10, margin_bottom=10))

        self.enable_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, hexpand=True, margin_bottom=15)
        self.config_box.append(self.enable_box)

        self.enable_label = Gtk.Label(label=gl.lm.get("enable"), hexpand=True, xalign=0)
        self.enable_box.append(self.enable_label)

        self.enable_switch = Gtk.Switch()
        self.enable_box.append(self.enable_switch)

        self.time_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, hexpand=True)
        self.config_box.append(self.time_box)

        self.time_label = Gtk.Label(label=gl.lm.get("screensaver-delay"), hexpand=True, xalign=0)
        self.time_box.append(self.time_label)

        self.time_spinner = Gtk.SpinButton.new_with_range(1, 60, 1)
        self.time_box.append(self.time_spinner)

        self.media_selector_label = Gtk.Label(label=gl.lm.get("media-to-show"), hexpand=True, xalign=0)
        self.config_box.append(self.media_selector_label)

        self.media_selector_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, halign=Gtk.Align.CENTER)
        self.config_box.append(self.media_selector_box)

        self.media_selector_button = Gtk.Button(label=gl.lm.get("select"), css_classes=["page-settings-media-selector"])
        self.media_selector_box.append(self.media_selector_button)

        self.progress_bar = Gtk.ProgressBar(hexpand=True, margin_top=10, text=gl.lm.get("background.processing"), fraction=0, show_text=True, visible=False)
        self.config_box.append(self.progress_bar)

        self.media_selector_image = Gtk.Image() # Will be bound to the button by self.set_thumbnail()

        self.loop_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, hexpand=True, margin_bottom=15)
        self.config_box.append(self.loop_box)

        self.loop_label = Gtk.Label(label=gl.lm.get("media-loop"), hexpand=True, xalign=0)
        self.loop_box.append(self.loop_label)

        self.loop_switch = Gtk.Switch()
        self.loop_box.append(self.loop_switch)

        self.fps_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, hexpand=True)
        self.config_box.append(self.fps_box)

        self.fps_label = Gtk.Label(label=gl.lm.get("fps"), hexpand=True, xalign=0)
        self.fps_box.append(self.fps_label)

        self.fps_spinner = Gtk.SpinButton.new_with_range(1, 30, 1)
        self.fps_box.append(self.fps_spinner)

        self.brightness_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, hexpand=True)
        self.config_box.append(self.brightness_box)

        self.brightness_label = Gtk.Label(label=gl.lm.get("brightness"), hexpand=True, xalign=0)
        self.brightness_box.append(self.brightness_label)

        self.scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, min=0, max=100, step=1)
        self.brightness_box.append(self.scale)

        # Signals get directly disconnected by disconnect_signals() but we have to connect them beforehand to prevent errors
        self.connect_signals()

        self.load_defaults_from_page()
    
    def connect_signals(self):
        self.overwrite_switch.connect("state-set", self.on_toggle_overwrite)
        self.enable_switch.connect("state-set", self.on_toggle_enable)
        self.time_spinner.connect("value-changed", self.on_change_time)
        self.media_selector_button.connect("clicked", self.on_choose_image)
        self.loop_switch.connect("state-set", self.on_toggle_loop)
        self.fps_spinner.connect("value-changed", self.on_change_fps)
        self.scale.connect("value-changed", self.on_change_brightness)

    def disconnect_signals(self):
        try:
            # FIXME: This doesn't work always
            self.overwrite_switch.disconnect_by_func(self.on_toggle_overwrite)
            self.enable_switch.disconnect_by_func(self.on_toggle_enable)
            self.time_spinner.disconnect_by_func(self.on_change_time)
            self.media_selector_button.disconnect_by_func(self.on_choose_image)
            self.loop_switch.disconnect_by_func(self.on_toggle_loop)
            self.fps_spinner.disconnect_by_func(self.on_change_fps)
            self.scale.disconnect_by_func(self.on_change_brightness)
        except:
            pass

    def load_defaults_from_page(self):
        self.disconnect_signals()
        # Verify if page exists
        if not hasattr(self.settings_page.deck_page.deck_controller, "active_page"):
            return
        if self.settings_page.deck_page.deck_controller.active_page == None:
            return

        original_values = None
        if hasattr(self.settings_page.deck_page.deck_controller.active_page, "screensaver"):
            original_values = self.settings_page.deck_page.deck_controller.active_page.dict["screensaver"].copy()
        # Set default values
        self.settings_page.deck_page.deck_controller.active_page.dict.setdefault("screensaver", {})
        overwrite = self.settings_page.deck_page.deck_controller.active_page.dict["screensaver"].setdefault("overwrite", False)
        enable = self.settings_page.deck_page.deck_controller.active_page.dict["screensaver"].setdefault("enable", False)
        path = self.settings_page.deck_page.deck_controller.active_page.dict["screensaver"].setdefault("path", None)
        loop = self.settings_page.deck_page.deck_controller.active_page.dict["screensaver"].setdefault("loop", False)
        fps = self.settings_page.deck_page.deck_controller.active_page.dict["screensaver"].setdefault("fps", 30)
        time = self.settings_page.deck_page.deck_controller.active_page.dict["screensaver"].setdefault("time-delay", 5)
        brightness = self.settings_page.deck_page.deck_controller.active_page.dict["screensaver"].setdefault("brightness", 75)

        # Update ui
        self.overwrite_switch.set_active(overwrite)
        self.enable_switch.set_active(enable)
        self.loop_switch.set_active(loop)
        self.fps_spinner.set_value(fps)
        self.time_spinner.set_value(time)
        self.scale.set_value(brightness)
        self.set_thumbnail(path)

        self.config_box.set_visible(overwrite)

        # Save if changed
        if original_values != self.settings_page.deck_page.deck_controller.active_page.dict["screensaver"]:
            self.settings_page.deck_page.deck_controller.active_page.save()

        self.connect_signals()


    def on_toggle_enable(self, toggle_switch, state):
        deck_controller = self.settings_page.deck_page.deck_controller
        deck_controller.active_page.dict["screensaver"]["enable"] = state
        deck_controller.active_page.save()

        deck_controller.screen_saver.set_enable(state)

        # Load screensaver onto controller
        deck_controller.load_screensaver(deck_controller.active_page)


    def on_toggle_overwrite(self, toggle_switch, state):
        deck_controller = self.settings_page.deck_page.deck_controller
        deck_controller.active_page.dict["screensaver"]["overwrite"] = state
        # Save
        deck_controller.active_page.save()

        # Update screensaver config box's visibility
        self.config_box.set_visible(state)

        # Load screensaver onto controller
        deck_controller.load_screensaver(deck_controller.active_page)

    def on_toggle_loop(self, toggle_switch, state):
        self.settings_page.deck_page.deck_controller.active_page.dict["screensaver"]["loop"] = state
        self.settings_page.deck_page.deck_controller.active_page.save()
        self.settings_page.deck_page.deck_controller.screen_saver.set_loop(state)

    def on_change_fps(self, spinner):
        self.settings_page.deck_page.deck_controller.active_page.dict["screensaver"]["fps"] = spinner.get_value_as_int()
        self.settings_page.deck_page.deck_controller.active_page.save()
        self.settings_page.deck_page.deck_controller.screen_saver.set_fps(spinner.get_value_as_int())

    def on_change_time(self, spinner):
        self.settings_page.deck_page.deck_controller.active_page.dict["screensaver"]["time-delay"] = spinner.get_value_as_int()
        self.settings_page.deck_page.deck_controller.active_page.save()
        self.settings_page.deck_page.deck_controller.screen_saver.set_time(spinner.get_value_as_int())

    def on_change_brightness(self, scale):
        self.settings_page.deck_page.deck_controller.active_page.dict["screensaver"]["brightness"] = scale.get_value()
        self.settings_page.deck_page.deck_controller.active_page.save()
        self.settings_page.deck_page.deck_controller.screen_saver.set_brightness(scale.get_value())

    def set_thumbnail(self, file_path):
        if file_path == None:
            return
        image = gl.media_manager.get_thumbnail(file_path)
        pixbuf = image2pixbuf(image)
        self.media_selector_image.set_from_pixbuf(pixbuf)
        self.media_selector_button.set_child(self.media_selector_image)

    def on_choose_image(self, button):
        self.settings_page.deck_page.deck_controller.active_page.dict.setdefault("screensaver", {})
        media_path = self.settings_page.deck_page.deck_controller.active_page.dict["screensaver"].setdefault("path", None)

        gl.app.let_user_select_asset(default_path=media_path, callback_func=self.update_image)

    def update_image(self, file_path):
        self.set_thumbnail(file_path)
        deck_controller = self.settings_page.deck_page.deck_controller
        deck_controller.active_page.dict.setdefault("screensaver", {})
        deck_controller.active_page.dict["screensaver"]["path"] = file_path
        # Save page
        deck_controller.active_page.save()

        deck_controller.load_screensaver(deck_controller.active_page)