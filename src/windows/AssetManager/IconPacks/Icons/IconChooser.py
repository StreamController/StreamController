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
import time
import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, GLib

# Import own modules
from src.windows.AssetManager.ChooserPage import ChooserPage
from src.windows.AssetManager.IconPacks.Icons.IconFlowBox import WallpaperFlowBox
from src.windows.AssetManager.IconPacks.Icons.IconPreview import IconPreview
from src.windows.AssetManager.IconPacks.Preview import IconPackPreview

# Import python modules
import os
from fuzzywuzzy import fuzz
from loguru import logger as log

# Import globals
import globals as gl

# Import typing
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from src.windows.AssetManager.AssetManager import AssetManager
    from src.backend.IconPackManagement.IconPack import IconPack
    from src.windows.AssetManager.IconPacks.Stack import IconPackChooserStack

class IconChooserPage(ChooserPage):
    def __init__(self, stack: "IconPackChooserStack", asset_manager: "AssetManager"):
        super().__init__()
        self.asset_manager = asset_manager
        self.stack = stack

        self.selected_icon: str = None

        self.build_finished = False
        gl.thread_pool.submit_ui_task(self.build)

    @log.catch
    def build(self):
        self.build_finished = False
        self.set_loading(True)
        
        self.type_box.set_visible(False)

        self.icon_flow = WallpaperFlowBox(IconPreview, self)
        self.icon_flow.set_factory(self.preview_factory)
        self.icon_flow.set_filter_func(self.filter_func)
        self.icon_flow.set_sort_func(self.sort_func)
        # Remove default scrolled window
        GLib.idle_add(self.main_box.remove, self.scrolled_window)
        # Add dynamic flow box
        GLib.idle_add(self.main_box.append, self.icon_flow)

        # Connect flow box select signal
        self.icon_flow.flow_box.connect("child-activated", self.on_child_activated)

        self.set_loading(False)
        
        self.build_finished = True
        self.stack.on_load_finished()

    def load_for_pack(self, pack: "IconPack"):
        self.icon_flow.set_item_list(pack.get_icons())
        self.icon_flow.show_range(0, 50)

    def select_icon(self, path) -> None:
        self.selected_icon = path

    def on_child_activated(self, flow_box, child):
        self.asset_manager.callback_func(child.icon.path, *self.asset_manager.callback_args, **self.asset_manager.callback_kwargs)
        self.asset_manager.close()
        self.asset_manager.destroy()

    def preview_factory(self, preview: IconPreview, icon):
        preview.set_icon(icon)
        if self.selected_icon == icon.path:
            self.icon_flow.flow_box.select_child(preview)
    
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
        self.icon_flow.show_range(0, 50)