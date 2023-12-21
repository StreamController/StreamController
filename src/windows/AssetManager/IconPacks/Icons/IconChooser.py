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

# Import typing
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from src.windows.AssetManager.AssetManager import AssetManager
    from src.backend.IconPackManagement.IconPack import IconPack

class IconChooser(ChooserPage):
    def __init__(self, asset_manager: "AssetManager"):
        super().__init__()
        self.asset_manager = asset_manager
        self.nav_box.set_visible(False)

        self.build()

    def build(self):
        self.icon_flow = IconFlowBox(self)
        self.scrolled_box.prepend(self.icon_flow)

    def load_for_pack(self, pack: "IconPack"):
        self.clear_flow_box()

        for icon in pack.get_icons():
            preview = IconPreview(self, icon)
            self.icon_flow.append(preview)

    def clear_flow_box(self):
        while self.icon_flow.get_first_child() is not None:
            self.icon_flow.remove(self.icon_flow.get_first_child())