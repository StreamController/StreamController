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

# Import own modules
from src.windows.AssetManager.ChooserPage import ChooserPage
from src.windows.AssetManager.IconPacks.Icons.IconFlowBox import IconFlowBox
from src.windows.AssetManager.IconPacks.Icons.IconPreview import IconPreview
from src.windows.AssetManager.IconPacks.Preview import IconPackPreview

# Import python modules
import os
from fuzzywuzzy import fuzz

# Import typing
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from src.windows.AssetManager.AssetManager import AssetManager
    from src.backend.IconPackManagement.IconPack import IconPack

class IconChooserPage(ChooserPage):
    def __init__(self, asset_manager: "AssetManager"):
        super().__init__()
        self.asset_manager = asset_manager

        self.build()

    def build(self):
        self.icon_flow = IconFlowBox(self, margin_bottom=15, margin_top=15, margin_start=15, margin_end=15)
        self.icon_flow.set_factory(self.preview_factory)
        self.icon_flow.set_sort_func(self.sort_func)
        self.icon_flow.set_filter_func(self.filter_func)
        # Remove default scrolled window
        self.remove(self.scrolled_window)
        # Add dynamic flow box
        self.append(self.icon_flow)

        # Connect flow box select signal
        self.icon_flow.flow_box.connect("child-activated", self.on_child_activated)

    def load_for_pack(self, pack: "IconPack"):
        for icon in pack.get_icons():
            self.icon_flow.add_item(icon)
            # preview = IconPreview(self, icon)
            # self.icon_flow.append(preview)
        self.icon_flow.load_items()

    def clear_flow_box(self):
        while self.icon_flow.get_first_child() is not None:
            self.icon_flow.remove(self.icon_flow.get_first_child())

    def on_child_activated(self, flow_box, child):
        self.asset_manager.callback_func(child.icon.path, *self.asset_manager.callback_args, **self.asset_manager.callback_kwargs)
        self.asset_manager.close()
        self.asset_manager.destroy()

    def preview_factory(self, item):
        return IconPreview(self, item)
    
    def filter_func(self, item) -> bool:
        search = self.search_entry.get_text()
        if search == "":
            return True

        file_name = os.path.splitext(os.path.basename(item.path))[0]
        if fuzz.ratio(file_name.lower(), search.lower()) < 50:
            return False
        return True

    def sort_func(self, item1, item2) -> bool:
        # return -1 if child1 should come before child2
        # return 1 if child1 should come after child2
        # return 0 if they are equal
        search = self.search_entry.get_text()
        if search == "":
            # Sort alphabetically
            if os.path.splitext(os.path.basename(item1.path))[0] < os.path.splitext(os.path.basename(item2.path))[0]:
                return -1
            if os.path.splitext(os.path.basename(item1.path))[0] > os.path.splitext(os.path.basename(item2.path))[0]:
                return 1
            return 0
        fuzz1 = fuzz.ratio(os.path.splitext(os.path.basename(item1.path))[0].lower(), search.lower())
        fuzz2 = fuzz.ratio(os.path.splitext(os.path.basename(item2.path))[0].lower(), search.lower())

        if fuzz1 > fuzz2:
            return -1
        elif fuzz1 < fuzz2:
            return 1
        
        return 0
    
    def on_search_changed(self, entry):
        self.icon_flow.invalidate_filter()
        self.icon_flow.invalidate_sort()