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
from src.windows.AssetManager.DynamicFlowBox import DynamicFlowBox

# Import typing
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from src.windows.AssetManager.IconPacks.Icons.IconChooser import IconChooser

class IconFlowBox(DynamicFlowBox):
    def __init__(self, base_class, icon_chooser: "IconChooser", *args, **kwargs):
        super().__init__(base_class=base_class, *args, **kwargs)
        self.CHILDREN_PER_PAGE = 150
        self.set_hexpand(True)

        self.callback_func = None
        self.callback_args = ()
        self.callback_kwargs = {}

        self.icon_chooser = icon_chooser