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
import gc
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


class Screensaver(Adw.PreferencesRow):
    def __init__(self, page_editor: "PageEditor", **kwargs):
        super().__init__(css_classes=["no-click"])
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

        self.time_spinner = Gtk.SpinButton.new_with_range(1, 24*60, 1)
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
        if not self.get_mapped():
            self.on_map_tasks.clear()
            self.on_map_tasks.append(lambda: self.load_defaults_from_page())
            return
        self.disconnect_signals()

        page_dict = self.page_editor.get_page_data()

        overwrite = page_dict.get("screensaver", {}).get("overwrite", False)
        enable = page_dict.get("screensaver", {}).get("enable", False)
        path = page_dict.get("screensaver", {}).get("path", None)
        loop = page_dict.get("screensaver", {}).get("loop", False)
        fps = page_dict.get("screensaver", {}).get("fps", 30)
        time = page_dict.get("screensaver", {}).get("time-delay", 5)
        brightness = page_dict.get("screensaver", {}).get("brightness", 75)

        # Update ui
        self.overwrite_switch.set_active(overwrite)
        self.enable_switch.set_active(enable)
        self.loop_switch.set_active(loop)
        self.fps_spinner.set_value(fps)
        self.time_spinner.set_value(time)
        self.scale.set_value(brightness)
        self.config_box.set_visible(overwrite)

        if path is not None:
            if os.path.isfile(path):
                self.set_thumbnail(path)

        self.connect_signals()


    def on_toggle_enable(self, toggle_switch, state):
        dict_data = self.page_editor.get_page_data()
        dict_data["screensaver"]["enable"] = state
        self.page_editor.set_page_data(dict_data,
                                        reload_brightness=False,
                                        reload_screensaver=True,
                                        reload_background=False,
                                        reload_inputs=False)


    def on_toggle_overwrite(self, toggle_switch, state):
        dict_data = self.page_editor.get_page_data()
        dict_data["screensaver"]["overwrite"] = state
        self.page_editor.set_page_data(dict_data,
                                        reload_brightness=False,
                                        reload_screensaver=True,
                                        reload_background=False,
                                        reload_inputs=False)

    def on_toggle_loop(self, toggle_switch, state):
        dict_data = self.page_editor.get_page_data()
        dict_data["screensaver"]["loop"] = state
        self.page_editor.set_page_data(dict_data,
                                        reload_brightness=False,
                                        reload_screensaver=True,
                                        reload_background=False,
                                        reload_inputs=False)

    def on_change_fps(self, spinner):
        dict_data = self.page_editor.get_page_data()
        dict_data["screensaver"]["fps"] = spinner.get_value_as_int()
        self.page_editor.set_page_data(dict_data,
                                        reload_brightness=False,
                                        reload_screensaver=True,
                                        reload_background=False,
                                        reload_inputs=False)

    def on_change_time(self, spinner):
        dict_data = self.page_editor.get_page_data()
        dict_data["screensaver"]["time-delay"] = round(spinner.get_value_as_int())
        self.page_editor.set_page_data(dict_data,
                                        reload_brightness=False,
                                        reload_screensaver=True,
                                        reload_background=False,
                                        reload_inputs=False)

    def on_change_brightness(self, scale):
        dict_data = self.page_editor.get_page_data()
        dict_data["screensaver"]["brightness"] = scale.get_value()
        self.page_editor.set_page_data(dict_data,
                                        reload_brightness=False,
                                        reload_screensaver=True,
                                        reload_background=False,
                                        reload_inputs=False)

    def set_thumbnail(self, file_path):
        if file_path == None:
            return

        image = gl.media_manager.get_thumbnail(file_path)
        pixbuf = image2pixbuf(image)

        self.media_selector_image.set_from_pixbuf(None)
        self.media_selector_image.pixbuf = None

        del self.media_selector_image.pixbuf

        self.media_selector_image.set_from_pixbuf(pixbuf)
        self.media_selector_button.set_child(self.media_selector_image)

        image.close()
        image = None
        pixbuf = None
        del image
        del pixbuf
        gc.collect()

    def on_choose_image(self, button):
        dict_data = self.page_editor.get_page_data()
        media_path = dict_data.get("screensaver", {}).get("path", None)

        gl.app.let_user_select_asset(default_path=media_path, callback_func=self.update_image)

    def update_image(self, file_path):
        self.set_thumbnail(file_path)
        dict_data = self.page_editor.get_page_data()
        dict_data["screensaver"]["path"] = file_path
        self.page_editor.set_page_data(dict_data,
                                        reload_brightness=False,
                                        reload_screensaver=True,
                                        reload_background=False,
                                        reload_inputs=False)