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

class DeckGroup(Adw.PreferencesGroup):
    def __init__(self, settings_page):
        super().__init__(title="Deck Settings", description="Applies only to current page")

        self.add(Brightness(settings_page))
        self.add(Screensaver(settings_page))

class Brightness(Adw.PreferencesRow):
    def __init__(self, settings_page: "PageSettings", **kwargs):
        super().__init__()
        self.settings_page = settings_page
        self.build()

    def build(self):
        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, hexpand=True,
                                margin_start=15, margin_end=15, margin_top=15, margin_bottom=15)
        self.set_child(self.main_box)

        self.label = Gtk.Label(label="Brightness", hexpand=True, xalign=0)
        self.main_box.append(self.label)

        self.scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, min=0, max=100, step=1)
        self.scale.set_draw_value(True)
        self.set_scale_initial_value()
        self.scale.connect("value-changed", self.on_value_changed)
        self.main_box.append(self.scale)

    def set_scale_initial_value(self):
        # Load default scalar value
        current_page = None
        if hasattr(self.settings_page.deck_page.deck_controller, "active_page"):
            current_page = self.settings_page.deck_page.deck_controller.active_page
        self.set_scale_from_page(current_page)

    def set_scale_from_page(self, page):
        if page == None:
            self.scale.set_sensitive(False)
            self.main_box.append(Gtk.Label(label="Error", hexpand=True, xalign=0, css_classes=["red-color"]))
            return

        brightness = page["brightness"]
        self.scale.set_value(brightness)

    def on_value_changed(self, scale):
        value = round(scale.get_value())
        # update value in page
        self.settings_page.deck_page.deck_controller.active_page["brightness"] = value
        self.settings_page.deck_page.deck_controller.active_page.save()
        # update deck without reload of page
        self.settings_page.deck_page.deck_controller.set_brightness(value)

class Screensaver(Adw.PreferencesRow):
    def __init__(self, settings_page: "PageSettings", **kwargs):
        super().__init__(css_classes=["no-click"])
        self.settings_page = settings_page
        self.build()
    
    def build(self):
        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, hexpand=True,
                                margin_start=15, margin_end=15, margin_top=15, margin_bottom=15)
        self.set_child(self.main_box)

        self.override_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, hexpand=True)
        self.main_box.append(self.override_box)

        self.override_label = Gtk.Label(label="Override deck's default screensaver settings", hexpand=True, xalign=0)
        self.override_box.append(self.override_label)

        self.override_switch = Gtk.Switch(margin_end=15)
        self.override_switch.connect("state-set", self.on_toggle_override)
        self.override_box.append(self.override_switch)

        self.config_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, hexpand=True, visible=False)
        self.main_box.append(self.config_box)

        self.config_box.append(Gtk.Separator(margin_top=10, margin_bottom=10))

        self.enable_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, hexpand=True, margin_bottom=15)
        self.config_box.append(self.enable_box)

        self.enable_label = Gtk.Label(label="Enable", hexpand=True, xalign=0)
        self.enable_box.append(self.enable_label)

        self.enable_switch = Gtk.Switch(margin_end=15)
        self.enable_switch.connect("state-set", self.on_toggle_enable)
        self.enable_box.append(self.enable_switch)

        self.time_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, hexpand=True)
        self.config_box.append(self.time_box)

        self.time_label = Gtk.Label(label="Enable after (mins)", hexpand=True, xalign=0)
        self.time_box.append(self.time_label)

        self.time_spinner = Gtk.SpinButton.new_with_range(1, 60, 1)
        self.time_spinner.connect("value-changed", self.on_change_time)
        self.time_box.append(self.time_spinner)

        self.media_selector_label = Gtk.Label(label="Media to show:", hexpand=True, xalign=0)
        self.config_box.append(self.media_selector_label)

        self.media_selector_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, halign=Gtk.Align.CENTER)
        self.config_box.append(self.media_selector_box)

        self.media_selector_button = Gtk.Button(label="Select", css_classes=["page-settings-media-selector"])
        # self.media_selector_button.connect("clicked", self.choose_with_file_dialog)
        self.media_selector_box.append(self.media_selector_button)

        self.loop_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, hexpand=True, margin_bottom=15)
        self.config_box.append(self.loop_box)

        self.loop_label = Gtk.Label(label="Loop", hexpand=True, xalign=0)
        self.loop_box.append(self.loop_label)

        self.loop_switch = Gtk.Switch(margin_end=15)
        self.loop_switch.connect("state-set", self.on_toggle_loop)
        self.loop_box.append(self.loop_switch)

        self.fps_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, hexpand=True)
        self.config_box.append(self.fps_box)

        self.fps_label = Gtk.Label(label="FPS", hexpand=True, xalign=0)
        self.fps_box.append(self.fps_label)

        self.fps_spinner = Gtk.SpinButton.new_with_range(1, 30, 1)
        self.fps_spinner.connect("value-changed", self.on_change_fps)
        self.fps_box.append(self.fps_spinner)

        self.load_defaults_from_page()

    def load_defaults_from_page(self):
        # Verify if page exists
        if not hasattr(self.settings_page.deck_page.deck_controller, "active_page"):
            return
        if self.settings_page.deck_page.deck_controller.active_page == None:
            return
        # Fetch infos
        enabled = self.settings_page.deck_page.deck_controller.active_page["screensaver"]["enable"]
        path = self.settings_page.deck_page.deck_controller.active_page["screensaver"]["path"]
        loop = self.settings_page.deck_page.deck_controller.active_page["screensaver"]["loop"]
        fps = self.settings_page.deck_page.deck_controller.active_page["screensaver"]["fps"]
        time = self.settings_page.deck_page.deck_controller.active_page["screensaver"]["time-delay"]

        # Update ui
        self.override_switch.set_active(enabled)
        self.enable_switch.set_active(enabled)
        self.loop_switch.set_active(loop)
        self.fps_spinner.set_value(fps)
        self.time_spinner.set_value(time)

        self.config_box.set_visible(enabled)


    def on_toggle_enable(self, toggle_switch, state):
        self.settings_page.deck_page.deck_controller.active_page["screensaver"]["enable"] = state


    def on_toggle_override(self, toggle_switch, state):
        self.settings_page.deck_page.deck_controller.active_page["screensaver"]["override"] = state

        # Update screensaver config box's visibility
        self.config_box.set_visible(state)

    def on_toggle_loop(self, toggle_switch, state):
        self.settings_page.deck_page.deck_controller.active_page["screensaver"]["loop"] = state

    def on_change_fps(self, spinner):
        self.settings_page.deck_page.deck_controller.active_page["screensaver"]["fps"] = spinner.get_value_as_int()

    def on_change_time(self, spinner):
        self.settings_page.deck_page.deck_controller.active_page["screensaver"]["time-delay"] = spinner.get_value_as_int()