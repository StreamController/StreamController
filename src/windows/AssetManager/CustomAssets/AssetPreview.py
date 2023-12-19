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
from gi.repository import Gtk, Adw, GdkPixbuf

# Import own modules
from src.windows.AssetManager.Preview import Preview


# Import typing
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from src.windows.AssetManager.CustomAssets.FlowBox import CustomAssetChooserFlowBox

class AssetPreview(Preview):
    def __init__(self, flow:"CustomAssetChooserFlowBox", asset:dict, *args, **kwargs):
        super().__init__(
            image_path=asset["thumbnail"],
            text=asset["name"],
        )
        self.asset = asset
        self.flow = flow


    def on_click_info(self, button):
        self.flow.asset_chooser.asset_manager.show_info_for_asset(self.asset)