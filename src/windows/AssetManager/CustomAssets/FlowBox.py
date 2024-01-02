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
from gi.repository import Gtk, Adw

# Import python modules
from fuzzywuzzy import fuzz

# Import globals
import globals as gl

# Import own modules
from src.backend.DeckManagement.HelperMethods import is_video
from src.windows.AssetManager.CustomAssets.AssetPreview import AssetPreview

# Import typing
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from src.windows.AssetManager.CustomAssets.Chooser import CustomAssetChooser


class CustomAssetChooserFlowBox(Gtk.Box):
    def __init__(self, asset_chooser, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.set_orientation(Gtk.Orientation.HORIZONTAL)
        self.set_hexpand(True)

        self.callback_func = None
        self.callback_args = ()
        self.callback_kwargs = {}

        self.asset_chooser:"CustomAssetChooser" = asset_chooser

        self.all_assets:list["AssetPreview"] = []

        self.build()

        self.flow_box.set_filter_func(self.filter_func)
        self.flow_box.set_sort_func(self.sort_func)


    def build(self):
        self.flow_box = Gtk.FlowBox(hexpand=True, orientation=Gtk.Orientation.HORIZONTAL)
        self.flow_box.connect("child-activated", self.on_child_activated)
        self.append(self.flow_box)

        for asset in gl.asset_manager.get_all():
            asset = AssetPreview(flow=self, asset=asset, width_request=100, height_request=100)
            self.flow_box.append(asset)

    def show_for_path(self, path, callback_func=None, *callback_args, **callback_kwargs):
        self.callback_func = callback_func
        self.callback_args = callback_args
        self.callback_kwargs = callback_kwargs

        i = 0
        while True:
            child = self.flow_box.get_child_at_index(i)
            if child == None:
                return
            if child.asset["internal-path"] == path:
                self.flow_box.select_child(child)
                return
            i += 1
            
    def filter_func(self, child):
        search_string = self.asset_chooser.search_entry.get_text()
        show_image = self.asset_chooser.image_button.get_active()
        show_video = self.asset_chooser.video_button.get_active()

        child_is_video = is_video(child.asset["internal-path"])

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
        search_string = self.asset_chooser.search_entry.get_text()

        if search_string == "":
            # Sort alphabetically
            if a.asset["name"] < b.asset["name"]:
                return -1
            if a.asset["name"] > b.asset["name"]:
                return 1
            return 0
        
        a_fuzz = fuzz.partial_ratio(search_string.lower(), a.asset["name"].lower())
        b_fuzz = fuzz.partial_ratio(search_string.lower(), b.asset["name"].lower())

        if a_fuzz > b_fuzz:
            return -1
        elif a_fuzz < b_fuzz:
            return 1
        
        return 0
    
    def on_child_activated(self, flow_box, child):
        if callable(self.callback_func):
            self.callback_func(child.asset["internal-path"], *self.callback_args, **self.callback_kwargs)
        self.asset_chooser.asset_manager.close()