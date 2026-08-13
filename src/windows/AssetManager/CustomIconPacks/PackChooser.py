"""
Author: Core447
Year: 2025

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
import zipfile
from fuzzywuzzy import fuzz
from loguru import logger as log

# Import own modules
from src.windows.AssetManager.ChooserPage import ChooserPage
from src.windows.AssetManager.CustomIconPacks.PackDialog import CustomIconPackDialog
from src.windows.AssetManager.CustomIconPacks.Preview import CustomIconPackPreview
from src.backend.IconPackManagement import CustomIconPack

# Import globals
import globals as gl

# Import typing
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from src.windows.AssetManager.AssetManager import AssetManager
    from src.windows.AssetManager.CustomIconPacks.Stack import CustomIconPackChooserStack


class CustomIconPackChooser(ChooserPage):
    def __init__(self, stack: "CustomIconPackChooserStack", asset_manager: "AssetManager"):
        super().__init__()
        self.asset_manager = asset_manager
        self.stack = stack

        self.build_finished = False
        self.build()

    @log.catch
    def build(self):
        self.type_box.set_visible(False)
        self.search_entry.set_placeholder_text("Search packs")

        self.all_icons_button = Gtk.Button(margin_start=15, tooltip_text="Search icons across all packs")
        self.all_icons_button.set_child(Adw.ButtonContent(icon_name="system-search-symbolic", label="All Icons"))
        self.all_icons_button.connect("clicked", self.on_all_icons_clicked)
        self.nav_box.append(self.all_icons_button)

        self.status_page = Adw.StatusPage(
            icon_name="folder-download-symbolic",
            title="No Custom Asset Packs",
            description="Drop a zip file with images here or use the New button to create a pack",
            vexpand=True
        )
        self.inside_box.append(self.status_page)

        self.flow_box = Gtk.FlowBox(hexpand=True, orientation=Gtk.Orientation.HORIZONTAL,
                                    selection_mode=Gtk.SelectionMode.NONE)
        self.flow_box.set_filter_func(self.filter_func)
        self.flow_box.connect("child-activated", self.on_child_activated)
        self.scrolled_box.prepend(self.flow_box)

        self.new_button = self.add_pill_button("New", tooltip="Create a new asset pack")
        self.new_button.connect("clicked", self.on_new_clicked)

        self.load()

        self.set_loading(False)

        self.build_finished = True
        self.stack.on_load_finished()

    def load(self):
        for pack in CustomIconPack.get_custom_icon_packs().values():
            self.flow_box.append(CustomIconPackPreview(self, pack))

        self.status_page.set_visible(self.flow_box.get_first_child() is None)

    def reload(self):
        while (child := self.flow_box.get_first_child()) is not None:
            self.flow_box.remove(child)

        self.load()

    def on_child_activated(self, flow_box, child: CustomIconPackPreview):
        self.stack.show_pack(child.pack)

    def on_all_icons_clicked(self, button):
        self.stack.show_all_icons()

    def on_new_clicked(self, button):
        CustomIconPackDialog(self).present(gl.asset_manager)

    def filter_func(self, child: CustomIconPackPreview) -> bool:
        search = self.search_entry.get_text().lower()
        if search == "":
            return True

        name = child.pack.name.lower()
        return search in name or fuzz.partial_ratio(name, search) >= 70

    def on_search_changed(self, entry):
        self.flow_box.invalidate_filter()

    ## Drag and drop

    def on_dnd_accept(self, drop, user_data):
        return True

    def on_dnd_drop(self, drop_target, value: Gdk.FileList, x, y):
        sources = []
        for file in value.get_files():
            path = file.get_path()
            if path is None:
                continue
            if os.path.isdir(path) or zipfile.is_zipfile(path) or CustomIconPack.is_supported_image(path):
                sources.append(path)
            else:
                log.warning(f"Cannot create an asset pack from {path}")

        if not sources:
            return False

        CustomIconPackDialog(self, sources=sources).present(gl.asset_manager)
        return True
