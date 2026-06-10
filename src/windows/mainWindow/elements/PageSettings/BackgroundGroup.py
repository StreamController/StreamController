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
from copy import copy

# Import globals
import globals as gl

# Import own modules
from src.backend.DeckManagement.ImageHelpers import image2pixbuf, is_transparent

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from src.windows.PageManager.elements.PageEditor import PageEditor

class BackgroundGroup(Adw.PreferencesGroup):
    def __init__(self, settings_page):
        super().__init__(title=gl.lm.get("background"), description=gl.lm.get("page-settings-only-current-page-hint"), margin_top=15)
        self.set_margin_top(50)
        self.media_row = BackgroundMediaRow(settings_page)
        self.add(self.media_row)


class BackgroundMediaRow(Adw.PreferencesRow):
    def __init__(self, page_editor: "PageEditor", **kwargs):
        super().__init__()
        self.page_editor: "PageEditor" = page_editor

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

        self.overwrite_label = Gtk.Label(label=gl.lm.get("page-settings-deck-overwrite-background"), hexpand=True, xalign=0)
        self.overwrite_box.append(self.overwrite_label)

        self.overwrite_switch = Gtk.Switch()
        self.overwrite_box.append(self.overwrite_switch)

        self.config_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, hexpand=True, visible=False)
        self.main_box.append(self.config_box)

        self.config_box.append(Gtk.Separator(hexpand=True, margin_top=10, margin_bottom=10))

        self.show_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, hexpand=True)
        self.config_box.append(self.show_box)

        self.show_label = Gtk.Label(label=gl.lm.get("page-settings-deck-show-background"), hexpand=True, xalign=0)
        self.show_box.append(self.show_label)
        self.show_switch = Gtk.Switch()
        self.show_box.append(self.show_switch)

        self.media_selector = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, halign=Gtk.Align.CENTER)
        self.config_box.append(self.media_selector)

        self.media_selector_image = Gtk.Image() # Will be bound to the button by self.set_thumbnail()

        self.media_selector_button = Gtk.Button(label=gl.lm.get("select"), css_classes=["page-settings-media-selector"])
        self.media_selector.append(self.media_selector_button)

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

        # Signals get directly disconnected by disconnect_signals() but we have to connect them beforehand to prevent errors
        self.connect_signals()

        self.load_defaults_from_page()

    def connect_signals(self):
        self.overwrite_switch.connect("state-set", self.on_toggle_overwrite)
        self.show_switch.connect("state-set", self.on_toggle_enable)
        self.media_selector_button.connect("clicked", self.on_choose_image)
        self.loop_switch.connect("state-set", self.on_toggle_loop)
        self.fps_spinner.connect("value-changed", self.on_change_fps)
        

    def disconnect_signals(self):
        try:
            self.overwrite_switch.disconnect_by_func(self.on_toggle_overwrite)
            self.show_switch.disconnect_by_func(self.on_toggle_enable)
            self.media_selector_button.disconnect_by_func(self.on_choose_image)
            self.loop_switch.disconnect_by_func(self.on_toggle_loop)
            self.fps_spinner.disconnect_by_func(self.on_change_fps)
        except TypeError as e:
            log.error(f"Don't panic, getting this error is normal: {e}")


    def load_defaults_from_page(self):
        if not self.get_mapped():
            self.on_map_tasks.clear()
            self.on_map_tasks.append(lambda: self.load_defaults_from_page())
            return
        self.disconnect_signals()

        page_dict = self.page_editor.get_page_data()

        overwrite = page_dict.get("background", {}).get("overwrite", False)
        show = page_dict.get("background", {}).get("show", False)
        file_path = page_dict.get("background", {}).get("path", None)
        loop = page_dict.get("background", {}).get("loop", True)
        fps = page_dict.get("background", {}).get("fps", 30)

        self.overwrite_switch.set_active(overwrite)
        self.show_switch.set_active(show)
        self.loop_switch.set_active(loop)
        self.fps_spinner.set_value(fps)

        # Set config box state
        self.config_box.set_visible(overwrite)

        self.set_thumbnail(file_path)

        self.connect_signals()

    def on_toggle_enable(self, toggle_switch, state):
        dict_data = self.page_editor.get_page_data()
        dict_data["background"]["show"] = state
        self.page_editor.set_page_data(dict_data,
                                        reload_brightness=False,
                                        reload_screensaver=False,
                                        reload_background=True,
                                        reload_inputs=False)

    def on_toggle_loop(self, toggle_switch, state):
        dict_data = self.page_editor.get_page_data()
        dict_data["background"]["loop"] = state
        self.page_editor.set_page_data(dict_data,
                                        reload_brightness=False,
                                        reload_screensaver=False,
                                        reload_background=True,
                                        reload_inputs=False)

    def on_change_fps(self, spinner):
        dict_data = self.page_editor.get_page_data()
        dict_data["background"]["fps"] = spinner.get_value_as_int()
        self.page_editor.set_page_data(dict_data,
                                        reload_brightness=False,
                                        reload_screensaver=False,
                                        reload_background=True,
                                        reload_inputs=False)

    def on_toggle_overwrite(self, toggle_switch, state):
        self.config_box.set_visible(state)
        # Update page
        dict_data = self.page_editor.get_page_data()
        dict_data["background"]["overwrite"] = state
        self.page_editor.set_page_data(dict_data,
                                        reload_brightness=False,
                                        reload_screensaver=False,
                                        reload_background=True,
                                        reload_inputs=False)

    def on_choose_image(self, button):
        dict_data = self.page_editor.get_page_data()
        media_path = dict_data.get("background", {}).get("path", None)

        gl.app.let_user_select_asset(default_path=media_path, callback_func=self.set_deck_background)

    def set_thumbnail(self, file_path):
        if file_path == None:
            self.media_selector_image.clear()
            return
        if file_path is None:
            return
        if not os.path.isfile(file_path):
            return
        image = gl.media_manager.get_thumbnail(file_path)
        pixbuf = image2pixbuf(image)
        if pixbuf is None:
            # This usually means that the provided image is a non RGB one
            dial = Gtk.AlertDialog(
                message="The chosen image doesn't seem to have RGB color channels.",
                detail="Please convert it in an app like GIMP.",
                modal=True
            )
            dial.show()
            return
        self.media_selector_image.pixbuf = None
        del self.media_selector_image.pixbuf
        self.media_selector_image.set_from_pixbuf(pixbuf)
        self.media_selector_button.set_child(self.media_selector_image)

    def set_deck_background(self, file_path: str) -> None:
        self.set_thumbnail(file_path)

        show = self.show_switch.get_active() and self.overwrite_switch.get_active()
        if show:
            self.set_background_to_page(file_path)

    def set_background_to_page(self, file_path):
        dict_data = self.page_editor.get_page_data()
        dict_data["background"]["path"] = file_path
        self.page_editor.set_page_data(dict_data,
                                        reload_brightness=False,
                                        reload_screensaver=False,
                                        reload_background=True,
                                        reload_inputs=False)