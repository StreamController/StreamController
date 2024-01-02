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
from src.windows.AssetManager.Preview import Preview

# Import globals
import globals as gl

# Import typing
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from src.windows.AssetManager.IconPacks.PackChooser import IconPackChooser
    from src.backend.IconPackManagement.Icon import Icon

class IconPreview(Preview):
    def __init__(self, icon_pack_chooser: "IconPackChooser", icon: "Icon"):
        super().__init__(
            image_path=icon.path,
            text=icon.name
        )
        self.icon = icon
        self.icon_pack_chooser = icon_pack_chooser

    def on_click_info(self, *args):
        self.icon_pack_chooser.asset_manager.show_info(
            internal_path = self.icon.path,
            licence_name = self.icon.get_attribution().get("license"),
            license_url = self.icon.get_attribution().get("license-url"),
            author = self.icon.get_attribution().get("copyright"),
            license_comment = self.icon.get_attribution().get("comment")
        )