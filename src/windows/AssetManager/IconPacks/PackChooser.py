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
import os

# Import own modules
from src.windows.AssetManager.ChooserPage import ChooserPage
from src.windows.AssetManager.IconPacks.FlowBox import IconPackFlowBox
from src.windows.AssetManager.IconPacks.Preview import IconPackPreview

# Import globals
import globals as gl

# Import typing
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from src.windows.AssetManager.AssetManager import AssetManager


class IconPackChooser(ChooserPage):
    def __init__(self, asset_manager: "AssetManager"):
        super().__init__()
        self.asset_manager = asset_manager

        self.build()

        self.load()

    def build(self):
        self.type_box.set_visible(False)

        self.icon_pack_chooser = IconPackFlowBox(self, orientation=Gtk.Orientation.HORIZONTAL, hexpand=True)
        self.scrolled_box.prepend(self.icon_pack_chooser)

        self.icon_pack_chooser.flow_box.connect("child-activated", self.on_child_activated)

    def load(self):
        flow_box = self.icon_pack_chooser.flow_box

        for name, pack in gl.icon_pack_manager.get_icon_packs().items():
            preview = IconPackPreview(self, pack)
            flow_box.append(preview)

    def on_child_activated(self, flow_box, child):
        # Load icons
        self.asset_manager.asset_chooser.icon_pack_chooser.icon_chooser.load_for_pack(child.pack)
        # Switch to icon chooser
        self.asset_manager.asset_chooser.icon_pack_chooser.set_visible_child_name("icon-chooser")
        # Show back button
        self.asset_manager.back_button.set_visible(True)
