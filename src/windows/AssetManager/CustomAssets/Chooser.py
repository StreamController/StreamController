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
import threading
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

        self.build_finished = False
        self.build_task_finished_tasks: list[callable] = []

        gl.thread_pool.submit_ui_task(self.build)

    @log.catch
    def build(self):
        self.build_finished = False
        self.asset_chooser = CustomAssetChooserFlowBox(self, orientation=Gtk.Orientation.HORIZONTAL, hexpand=True)
        GLib.idle_add(self.scrolled_box.prepend, self.asset_chooser)

        self.browse_files_button = Gtk.Button(label=gl.lm.get("asset-chooser.custom.browse-files"), margin_top=15)
        self.browse_files_button.connect("clicked", self.on_browse_files_clicked)
        GLib.idle_add(self.main_box.append, self.browse_files_button)

        self.load_defaults()

        self.set_loading(False)

        self.build_finished = True
        for task in self.build_task_finished_tasks:
            task()

    def on_dnd_accept(self, drop, user_data):
        return True
    
    def on_dnd_drop(self, drop_target, value: Gdk.FileList, x, y):
        paths = value.get_files()
        self.add_files(paths)
        return True
    
    def add_asset(self, asset: dict) -> None:
        preview = AssetPreview(self.asset_chooser, asset, width_request=100, height_request=100)
        GLib.idle_add(self.asset_chooser.flow_box.append, preview)
    
    def add_files(self, files: list) -> None:
        gl.asset_manager.set_cursor_from_name("wait")
        for path in files:

            url = path.get_uri()
            path = path.get_path()

            # gl.asset_manager_backend.add_custom_media_set_by_ui(url=url, path=path)
            gl.thread_pool.submit_background_task(gl.asset_manager_backend.add_custom_media_set_by_ui, url, path)

        gl.asset_manager.set_cursor_from_name("default")

    def show_for_path(self, path):
        if not self.build_finished:
            self.build_task_finished_tasks.append(lambda: self.asset_chooser.show_for_path(path))
            return
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