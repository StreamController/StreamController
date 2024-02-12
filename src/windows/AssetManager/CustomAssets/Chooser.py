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
from gi.repository import Gtk, Adw, Gdk

# Import python modules
import os
from loguru import logger as log

# Import own modules
from src.windows.AssetManager.ChooserPage import ChooserPage
from src.windows.AssetManager.CustomAssets.FlowBox import CustomAssetChooserFlowBox
from src.windows.AssetManager.CustomAssets.AssetPreview import AssetPreview
from src.backend.DeckManagement.HelperMethods import download_file

# Import globals
import globals as gl

# Import typing modules
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from src.windows.AssetManager.AssetManager import AssetManager

class CustomAssetChooser(ChooserPage):
    def __init__(self, asset_manager: "AssetManager"):
        super().__init__()
        self.asset_manager = asset_manager

        self.build()

        self.load_defaults()

    def build(self):
        self.asset_chooser = CustomAssetChooserFlowBox(self, orientation=Gtk.Orientation.HORIZONTAL, hexpand=True)
        self.scrolled_box.prepend(self.asset_chooser)

    def on_dnd_accept(self, drop, user_data):
        return True
    
    def on_dnd_drop(self, drop_target, value: Gdk.FileList, x, y):
        paths = value.get_files()
        for path in paths:
            # data = path.get_data()
            url = path.get_uri()
            path = path.get_path()

            if path is None and url is not None:
                # Download file from url
                path = download_file(url=url, path="cache/downloads")

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
            self.asset_chooser.flow_box.append(AssetPreview(flow=self, asset=asset, width_request=100, height_request=100))
        return True

    def show_for_path(self, path):
        self.asset_chooser.show_for_path(path)

    def on_video_toggled(self, button):
        settings = gl.settings_manager.load_settings_from_file(os.path.join(gl.DATA_PATH, "settings", "ui", "AssetManager.json"))
        settings["video-toggle"] = button.get_active()
        gl.settings_manager.save_settings_to_file(os.path.join(gl.DATA_PATH, "settings", "ui", "AssetManager.json"), settings)

        # Update ui
        self.asset_chooser.flow_box.invalidate_filter()

    def on_image_toggled(self, button):
        settings = gl.settings_manager.load_settings_from_file(os.path.join(gl.DATA_PATH, "settings", "ui", "AssetManager.json"))
        settings["image-toggle"] = button.get_active()
        gl.settings_manager.save_settings_to_file(os.path.join(gl.DATA_PATH, "settings", "ui", "AssetManager.json"), settings)

        # Update ui
        self.asset_chooser.flow_box.invalidate_filter()

    def load_defaults(self):
        settings = gl.settings_manager.load_settings_from_file(os.path.join(gl.DATA_PATH, "settings", "ui", "AssetManager.json"))
        self.video_button.set_active(settings.get("video-toggle", True))
        self.image_button.set_active(settings.get("image-toggle", True))

    def on_search_changed(self, entry):
        self.asset_chooser.flow_box.invalidate_sort()