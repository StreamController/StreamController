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

from src.backend.DeckManagement.HelperMethods import is_video


gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, GLib, Gio, Gdk, GObject, GdkPixbuf

# Import Python modules
from loguru import logger as log
from fuzzywuzzy import fuzz
from decord import VideoReader
from decord import cpu
from PIL import Image
import os
from functools import lru_cache
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from src.windows.mainWindow.mainWindow import MainWindow

# Import globals
import globals as gl

# Import own modules
from src.backend.DeckManagement.ImageHelpers import image2pixbuf

class AssetManager(Gtk.ApplicationWindow):
    def __init__(self, main_window: "MainWindow", *args, **kwargs):
        super().__init__(
            title="Asset Manager",
            default_width=1050,
            default_height=750,
            transient_for=main_window,
            *args, **kwargs
            )
        self.main_window = main_window
        self.build()
        self.load_defaults()

    def build(self):
        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, hexpand=True, vexpand=False,
                            margin_start=15, margin_end=15, margin_top=15, margin_bottom=15)
        self.set_child(self.main_box)

        self.nav_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, hexpand=True, vexpand=False, margin_bottom=15)
        self.main_box.append(self.nav_box)

        self.search_entry = Gtk.SearchEntry(placeholder_text="Search", hexpand=True)
        self.search_entry.connect("search-changed", self.on_search_changed)
        self.nav_box.append(self.search_entry)

        self.type_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, css_classes=["linked"], margin_start=15)
        self.nav_box.append(self.type_box)

        self.video_button = Gtk.ToggleButton(icon_name="view-list-video-symbolic", css_classes=["blue-toggle-button"])
        self.video_button.connect("toggled", self.on_video_toggled)
        self.type_box.append(self.video_button)

        self.image_button = Gtk.ToggleButton(icon_name="view-list-images-symbolic", css_classes=["blue-toggle-button"])
        self.image_button.connect("toggled", self.on_image_toggled)
        self.type_box.append(self.image_button)

        self.scrolled_window = Gtk.ScrolledWindow(hexpand=True, vexpand=True)
        self.main_box.append(self.scrolled_window)

        self.scrolled_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, hexpand=True, vexpand=False,
                                margin_top=5, margin_bottom=5)
        self.scrolled_window.set_child(self.scrolled_box)

        self.inside_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, hexpand=True, vexpand=False)
        self.scrolled_box.append(self.inside_box)

        self.asset_chooser = AssetChooser(self, orientation=Gtk.Orientation.HORIZONTAL, hexpand=True)
        self.scrolled_box.append(self.asset_chooser)

        # Add vexpand box to the bottom to avoid unwanted stretching of the children
        self.scrolled_box.append(Gtk.Box(vexpand=True, hexpand=True))

    def show_for_path(self, path, callback_func=None, *callback_args, **callback_kwargs):
        if not callable(callback_func):
            log.error("callback_func is not callable")
        self.asset_chooser.show_for_path(path, callback_func, *callback_args, **callback_kwargs)

        self.present()

    def on_video_toggled(self, button):
        settings = gl.settings_manager.load_settings_from_file("settings/ui/AssetManager.json")
        settings["video-toggle"] = button.get_active()
        gl.settings_manager.save_settings_to_file("settings/ui/AssetManager.json", settings)

        # Update ui
        self.asset_chooser.flow_box.invalidate_filter()

    def on_image_toggled(self, button):
        settings = gl.settings_manager.load_settings_from_file("settings/ui/AssetManager.json")
        settings["image-toggle"] = button.get_active()
        gl.settings_manager.save_settings_to_file("settings/ui/AssetManager.json", settings)

        # Update ui
        self.asset_chooser.flow_box.invalidate_filter()

    def load_defaults(self):
        settings = gl.settings_manager.load_settings_from_file("settings/ui/AssetManager.json")
        self.video_button.set_active(settings.get("video-toggle", True))
        self.image_button.set_active(settings.get("image-toggle", True))

    def on_search_changed(self, entry):
        self.asset_chooser.flow_box.invalidate_sort()

class AssetChooser(Gtk.Box):
    def __init__(self, asset_manager, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.set_orientation(Gtk.Orientation.HORIZONTAL)
        self.set_hexpand(True)

        self.callback_func = None
        self.callback_args = ()
        self.callback_kwargs = {}

        self.asset_manager:AssetManager = asset_manager

        self.all_assets:list[AssetPreview] = []

        self.build()

        self.flow_box.set_filter_func(self.filter_func)
        self.flow_box.set_sort_func(self.sort_func)


    def build(self):
        self.flow_box = Gtk.FlowBox(hexpand=True, orientation=Gtk.Orientation.HORIZONTAL)
        self.append(self.flow_box)

        for asset in gl.asset_manager.get_all():
            asset = AssetPreview(asset["name"], asset["thumbnail"], asset["internal-path"], width_request=100, height_request=100)
            self.flow_box.append(asset)

    def show_for_path(self, path, callback_func=None, *callback_args, **callback_kwargs):
        self.callback_func = callback_func
        self.callback_args = callback_args
        self.callback_kwargs = callback_kwargs

        for i in range(1, 100):
            child = self.flow_box.get_child_at_index(i)
            if child == None:
                return
            if child.asset_path == path:
                self.flow_box.select_child(child)
                return
            
    def filter_func(self, child):
        search_string = self.asset_manager.search_entry.get_text()
        show_image = self.asset_manager.image_button.get_active()
        show_video = self.asset_manager.video_button.get_active()

        child_is_video = is_video(child.asset_path)

        if child_is_video and not show_video:
            return False
        if not child_is_video and not show_image:
            return False
        
        if search_string == "":
            return True
        
        fuzz_score = fuzz.partial_ratio(search_string.lower(), child.name.lower())
        if fuzz_score < 40:
            return False
        
        return True
    
    def sort_func(self, a, b):
        search_string = self.asset_manager.search_entry.get_text()

        if search_string == "":
            # Sort alphabetically
            if a.name < b.name:
                return -1
            if a.name > b.name:
                return 1
            return 0
        
        a_fuzz = fuzz.partial_ratio(search_string.lower(), a.name.lower())
        b_fuzz = fuzz.partial_ratio(search_string.lower(), b.name.lower())

        if a_fuzz > b_fuzz:
            return -1
        elif a_fuzz < b_fuzz:
            return 1
        
        return 0


class AssetPreview(Gtk.FlowBoxChild):
    def __init__(self, name, thumbnail_path, asset_path, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.set_css_classes(["asset-preview"])
        self.set_margin_start(5)
        self.set_margin_end(5)
        self.set_margin_top(5)
        self.set_margin_bottom(5)

        self.name = name
        self.thumbnail_path = thumbnail_path
        self.asset_path = asset_path

        self.build()

    def build(self):
        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, width_request=250, height_request=180)
        self.set_child(self.main_box)

        self.picture = Gtk.Picture(width_request=250, height_request=180, overflow=Gtk.Overflow.HIDDEN, content_fit=Gtk.ContentFit.COVER,
                                   hexpand=False, vexpand=False, keep_aspect_ratio=True)
        self.pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(self.thumbnail_path,
                                                              width=250,
                                                              height=180,
                                                              preserve_aspect_ratio=True)
        
        self.picture.set_pixbuf(self.pixbuf)
        self.main_box.append(self.picture)

        self.label = Gtk.Label(label=self.name, xalign=Gtk.Align.CENTER)
        self.main_box.append(self.label)