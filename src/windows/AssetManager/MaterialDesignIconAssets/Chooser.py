"""
Author: gensyn
Year: 2025

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
any later version.

This programm comes with ABSOLUTELY NO WARRANTY!

You should have received a copy of the GNU General Public License
along with this program. If not, see <https://www.gnu.org/licenses/>.
"""
import gi

from windows.AssetManager.MaterialDesignIconAssets.Paginator import MaterialDesignIconsChooserPaginator

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, GLib

# Import own modules
from src.windows.AssetManager.ChooserPage import ChooserPage

# Import typing modules
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.windows.AssetManager.AssetManager import AssetManager


class MaterialDesignIconAssetChooser(ChooserPage):
    def __init__(self, asset_manager: "AssetManager"):
        super().__init__()
        self.asset_manager = asset_manager
        self.nav_box.remove(self.type_box)

        self.asset_chooser = MaterialDesignIconsChooserPaginator(self, orientation=Gtk.Orientation.HORIZONTAL,
                                                                 hexpand=True)
        GLib.idle_add(self.scrolled_box.prepend, self.asset_chooser)

        self.timeout_id = None

        self.set_loading(False)

    def on_search_changed(self, *_):
        self.asset_chooser.on_search_changed()
