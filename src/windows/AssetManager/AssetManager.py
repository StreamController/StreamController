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
from gi.repository import Gtk, Adw, GLib, Gio, Gdk, GObject

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
        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, hexpand=True, vexpand=True,
                            margin_start=15, margin_end=15, margin_top=15, margin_bottom=15)
        self.set_child(self.main_box)

        self.nav_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, hexpand=True, vexpand=False, margin_bottom=3)
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

        self.scrolled_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, hexpand=False, vexpand=False,
                                margin_top=5, margin_bottom=5)
        self.scrolled_window.set_child(self.scrolled_box)

        self.asset_chooser = AssetChooser(self)
        self.scrolled_box.append(self.asset_chooser)

    def show_for_path(self, path, callback_func=None, *callback_args, **callback_kwargs):
        if not callable(callback_func):
            log.error("callback_func is not callable")
        self.asset_chooser.show_for_path(path, callback_func, *callback_args, **callback_kwargs)

    def on_video_toggled(self, button):
        settings = gl.settings_manager.load_settings_from_file("settings/ui/AssetManager.json")
        settings["video-toggle"] = button.get_active()
        gl.settings_manager.save_settings_to_file("settings/ui/AssetManager.json", settings)

        # Update ui
        self.on_search_changed(self.search_entry)

    def on_image_toggled(self, button):
        settings = gl.settings_manager.load_settings_from_file("settings/ui/AssetManager.json")
        settings["image-toggle"] = button.get_active()
        gl.settings_manager.save_settings_to_file("settings/ui/AssetManager.json", settings)

        # Update ui
        self.on_search_changed(self.search_entry)

    def load_defaults(self):
        settings = gl.settings_manager.load_settings_from_file("settings/ui/AssetManager.json")
        self.video_button.set_active(settings.get("video-toggle", True))
        self.image_button.set_active(settings.get("image-toggle", True))

    def on_search_changed(self, entry):
        self.asset_chooser.filter_assets(self.search_entry.get_text())
        self.asset_chooser.list_store.sort(self.asset_chooser.sort_func)

class AssetChooser(Gtk.GridView):
    def __init__(self, asset_manager, *args, **kwargs):
        super().__init__()

        self.callback_func = None
        self.callback_args = ()
        self.callback_kwargs = {}

        self.asset_manager:AssetManager = asset_manager

        self.all_assets:list[Asset] = []

        self.build()
        self.init_dnd()

    def build(self):
        self.list_store = Gio.ListStore()
        for asset in gl.asset_manager.get_all():
                asset = Asset(asset["name"], asset["internal-path"])
                self.list_store.append(asset)
                self.all_assets.append(asset)

        self.single_selection = Gtk.SingleSelection(can_unselect=True, autoselect=False)
        self.single_selection.unselect_all()
        self.single_selection.set_model(self.list_store)
        self.single_selection.connect("selection-changed", self.on_selected_item_changed)

        self.set_model(self.single_selection)

        self.factory = Gtk.SignalListItemFactory()
        def factory_setup(fact, item):
            item.box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, width_request=250)
            item.set_child(item.box)

            item.picture = Gtk.Picture(vexpand=True, width_request=250, height_request=180, overflow=Gtk.Overflow.HIDDEN, content_fit=Gtk.ContentFit.COVER)
            item.box.append(item.picture)

            item.label = Gtk.Label()
            item.box.append(item.label)


        self.factory.connect("setup", factory_setup)

        def get_first_frame(video_path):
            vr = VideoReader(video_path)
            return vr[0]

        def factory_bind(fact, item):
            item.label.set_text(item.get_item().name)

            splitext = os.path.splitext(item.get_item().image_path)
            if len(splitext) < 2:
                return
            media_ext = splitext[1][1:].lower() # Remove the dot from the extension
            if media_ext in gl.image_extensions:
                item.picture.set_file(Gio.File.new_for_path(item.get_item().image_path))
            elif media_ext in gl.video_extensions:
                first_frame = get_first_frame(item.get_item().image_path)
                first_frame = Image.fromarray(first_frame.asnumpy())
                pixbuf = image2pixbuf(first_frame)
                item.picture.set_pixbuf(pixbuf)


        self.factory.connect("bind", factory_bind)

        self.set_factory(self.factory)

        # Sort assets
        self.list_store.sort(self.sort_func)

    def filter_assets(self, search_string):
        self.list_store.freeze_notify()
        self.list_store.remove_all()
        # if search_string == "":
        #     # Add all
        #     for asset in self.all_assets:
        #         self.list_store.append(asset)
        #     return
        
        for asset in self.all_assets:
            path = asset.image_path
            media_file_name = self.get_basename(path)

            if search_string != "":
                fuzz_score = self.get_ratio(self.get_lower(search_string), self.get_lower(media_file_name))
                if fuzz_score < 20:
                    continue

            media_spli = self.get_splitext(media_file_name)
            if len(media_spli) < 2:
                continue
            media_ext = self.get_lower(media_spli[1][1:]) # Remove the dot from the extension
            if media_ext in gl.image_extensions and not self.asset_manager.image_button.get_active():
                continue
            if media_ext in gl.video_extensions and not self.asset_manager.video_button.get_active():
                continue

            # Add to list store
            self.list_store.append(asset)

        self.list_store.thaw_notify()

    @lru_cache(maxsize=None)
    def get_lower(self, string):
        return string.lower()
    
    @lru_cache(maxsize=None)
    def get_splitext(self, path):
        return os.path.splitext(path)
    
    @lru_cache(maxsize=None)
    def get_basename(self, path):
        return os.path.basename(path)


    def get_hide_item_based_on_search(self, item, search_string):
        if search_string == "":
            return False

        image_path = item.get_item().image_path
        file_name = os.path.basename(image_path)

        fuzz_score = self.get_ratio(search_string.lower(), file_name.lower())
        if fuzz_score < 50:
            return True
        
        image_type = os.path.splitext(image_path)[1].lower()

        if image_type in gl.image_extensions and not self.asset_manager.image_toggle.get_active():
            return True
        if image_type in gl.video_extensions and not self.asset_manager.video_toggle.get_active():
            return True

        return False
    
    def on_selected_item_changed(self, selection, position, n_items):
        selected_item = selection.get_selected_item()
        if selected_item == None:
            return
        print(f"Selected item: {selected_item.image_path}")
        # Call callback
        if self.callback_func == None:
            return
        if not callable(self.callback_func):
            return
        
        self.asset_manager.hide()
        self.callback_func(selected_item.image_path, *self.callback_args, **self.callback_kwargs)

    def show_for_path(self, path, callback_func=None, *callback_args, **callback_kwargs):    
        self.asset_manager.present()
        if not callable(callback_func):
            log.error("callback_func is not callable")

        # Setup callback
        self.callback_func = callback_func
        self.callback_args = callback_args
        self.callback_kwargs = callback_kwargs
        
        if path == None:
            # Deselect all
            self.single_selection.unselect_all()
            return

        for i, item in enumerate(self.list_store):
            if item.image_path == path:
                self.single_selection.select_item(i, True)
                return

    def init_dnd(self):
        dnd_target = Gtk.DropTarget.new(Gdk.FileList, Gdk.DragAction.COPY)
        dnd_target.connect("drop", self.on_dnd_drop)
        dnd_target.connect("accept", self.on_dnd_accept)
        self.add_controller(dnd_target)

    def on_dnd_accept(self, drop, user_data):
        return True
    
    def on_dnd_drop(self, drop_target, value, x, y):
        paths = value.get_files()
        print(len(paths))
        for path in paths:
            path = path.get_path()
            if path == None:
                continue
            if not os.path.exists(path):
                continue
            if not os.path.splitext(path)[1] not in ["png", "jpg", "jpeg", "gif", "GIF", "MP4", "mp4", "mov", "MOV"]:
                continue
            asset_id = gl.asset_manager.add(asset_path=path)
            if asset_id == None:
                continue
            asset = gl.asset_manager.get_by_id(asset_id)
            self.list_store.append(Asset(asset["name"], asset["internal-path"]))
        return True
    @lru_cache(maxsize=None)
    def sort_func(self, item1, item2):
        search_string = self.asset_manager.search_entry.get_text().lower()

        item1_file_name = os.path.basename(item1.name)
        item2_file_name = os.path.basename(item2.name)

        if search_string == "":
            # sort alphabetically
            if item1_file_name < item2_file_name:
                return -1
            if item1_file_name > item2_file_name:
                return 1
            return 0

        item1_fuzz = self.get_ratio(item1_file_name, search_string)
        item2_fuzz = self.get_ratio(item2_file_name, search_string)

        if item1_fuzz > item2_fuzz:
            return -1
        elif item1_fuzz < item2_fuzz:
            return 1
        return 0
    
    @lru_cache(maxsize=None)
    def get_ratio(self, string1, string2):
        return fuzz.ratio(string1, string2)


class Asset(GObject.Object):
    name = GObject.Property(type=str)
    image_path = GObject.Property(type=str)
    def __init__(self, name, image_path):
        super().__init__()
        self.name = name
        self.image_path = image_path