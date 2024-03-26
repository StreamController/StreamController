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
from gi.repository import Gtk, Adw, Gdk, GLib

# Import python modules
import os
from loguru import logger as log

# Import own modules
from src.windows.AssetManager.ChooserPage import ChooserPage
from src.windows.AssetManager.CustomAssets.FlowBox import CustomAssetChooserFlowBox
from src.windows.AssetManager.CustomAssets.AssetPreview import AssetPreview

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

        self.browse_files_button = Gtk.Button(label=gl.lm.get("asset-chooser.custom.browse-files"), margin_top=15)
        self.browse_files_button.connect("clicked", self.on_browse_files_clicked)
        self.append(self.browse_files_button)

    def on_dnd_accept(self, drop, user_data):
        return True
    
    def on_dnd_drop(self, drop_target, value: Gdk.FileList, x, y):
        paths = value.get_files()
        self.add_files(paths)
        return True
    
    def add_asset(self, asset: dict) -> None:
        preview = AssetPreview(self.asset_chooser, asset, width_request=100, height_request=100)
        self.asset_chooser.flow_box.append(preview)
    
    def add_files(self, files: list) -> None:
        for path in files:

            url = path.get_uri()
            path = path.get_path()

            gl.asset_manager_backend.add_custom_media_set_by_ui(url=url, path=path)
            continue

            if path is None and url is not None:
                # Lower domain and remove point
                extension = os.path.splitext(url)[1].lower().replace(".", "")
                if extension not in (set(gl.video_extensions) | set(gl.image_extensions)):
                    # Not a valid url
                    dial = Gtk.AlertDialog(
                        message="The image is invalid.",
                        detail="You can only use urls directly pointing to images (not directly from Google).",
                        modal=True
                    )
                    dial.show()
                    continue

                os.makedirs(os.path.join(gl.DATA_PATH, "cache", "downloads"), exist_ok=True)
                # Download file from url
                path = download_file(url=url, path=os.path.join(gl.DATA_PATH, "cache", "downloads"))

            if path == None:
                continue
            if not os.path.exists(path):
                continue
            if not os.path.splitext(path)[1] not in ["png", "jpg", "jpeg", "gif", "GIF", "MP4", "mp4", "mov", "MOV"]:
                continue
            asset_id = gl.asset_manager_backend.add(asset_path=path)
            if asset_id == None:
                continue
            asset = gl.asset_manager_backend.get_by_id(asset_id)
            self.asset_chooser.flow_box.append(AssetPreview(flow=self, asset=asset, width_request=100, height_request=100))

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

    def on_browse_files_clicked(self, button):
        ChooseFileDialog(self) #TODO: Change to Xdp Portal call


class ChooseFileDialog(Gtk.FileDialog):
    def __init__(self, custom_asset_chooser: CustomAssetChooser):
        super().__init__(title=gl.lm.get("asset-chooser.custom.browse-files.dialog.title"),
                         accept_label=gl.lm.get("asset-chooser.custom.browse-files.dialog.select-button"))
        self.custom_asset_chooser = custom_asset_chooser
        self.open_multiple(callback=self.callback)

    def callback(self, dialog, result):
        try:
            selected_files = self.open_multiple_finish(result)
        except GLib.Error as err:
            log.error(err)
            return
        
        self.custom_asset_chooser.add_files(selected_files)