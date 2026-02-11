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

        threading.Thread(target=self.build).start()

    @log.catch
    def build(self):
        self.build_finished = False
        self.asset_chooser = CustomAssetChooserFlowBox(self, orientation=Gtk.Orientation.HORIZONTAL, hexpand=True)
        GLib.idle_add(self.scrolled_box.prepend, self.asset_chooser)
        
        # Connect selection change signal
        self.asset_chooser.connect("selection-changed", self.on_selection_changed)

        # Add bulk action buttons
        bulk_actions_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5, margin_top=5, margin_bottom=10)
        self.main_box.append(bulk_actions_box)
        
        self.delete_selected_button = Gtk.Button(label="Delete Selected", css_classes=["destructive-action"], sensitive=False)
        self.delete_selected_button.connect("clicked", self.on_delete_selected)
        bulk_actions_box.append(self.delete_selected_button)
        
        self.select_all_button = Gtk.Button(label="Select All", css_classes=["suggested-action"])
        self.select_all_button.connect("clicked", self.on_select_all)
        bulk_actions_box.append(self.select_all_button)
        
        self.clear_selection_button = Gtk.Button(label="Clear Selection")
        self.clear_selection_button.connect("clicked", self.on_clear_selection)
        bulk_actions_box.append(self.clear_selection_button)

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
            threading.Thread(target=gl.asset_manager_backend.add_custom_media_set_by_ui, args=(url, path), name="add_custom_media_set_by_ui").start()

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

    def on_selection_changed(self, flow_box):
        selected_count = len(flow_box.get_selected_children())
        self.delete_selected_button.set_sensitive(selected_count > 0)
        self.clear_selection_button.set_sensitive(selected_count > 0)
    
    def on_delete_selected(self, button):
        self.asset_chooser.delete_selected_assets()
    
    def on_select_all(self, button):
        self.asset_chooser.select_all()
    
    def on_clear_selection(self, button):
        self.asset_chooser.clear_selection()
    
    def auto_add_selected_assets(self):
        """Automatically add selected assets when window closes"""
        if callable(self.asset_manager.callback_func):
            import threading
            callback_thread = threading.Thread(target=self.confirm_selection_thread, args=(), name="auto_add_thread")
            callback_thread.start()
    
    @log.catch
    def confirm_selection_thread(self):
        # Get all selected children and call callback for each
        selected_children = self.asset_chooser.get_selected_children()
        if selected_children:
            for child in selected_children:
                self.asset_manager.callback_func(child.asset["internal-path"],
                                              *self.asset_manager.callback_args,
                                              **self.asset_manager.callback_kwargs)
    
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
