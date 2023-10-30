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

# Import Python modules
from loguru import logger as log

# Import own modules
from src.windows.mainWindow.elements.RightArea.elements.IconSelector import IconSelector
from src.windows.mainWindow.elements.RightArea.elements.LabelEditor import LabelEditor
from src.windows.mainWindow.elements.RightArea.elements.ActionEditor import ActionEditor

class RightArea(Gtk.Box):
    def __init__(self, main_window, **kwargs):
        super().__init__(**kwargs)
        self.main_window = main_window
        self.build()

    def build(self):
        self.scrolled_window = Gtk.ScrolledWindow(hexpand=True, vexpand=True)
        self.append(self.scrolled_window)

        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, hexpand=True, vexpand=True)
        self.scrolled_window.set_child(self.main_box)

        self.icon_selector = IconSelector(self, halign=Gtk.Align.CENTER, margin_top=75)
        self.main_box.append(self.icon_selector)

        self.label_editor = LabelEditor(self, halign=Gtk.Align.CENTER, margin_top=25)
        self.main_box.append(self.label_editor)

        self.action_editor = ActionEditor(self, halign=Gtk.Align.CENTER, margin_top=25)
        self.main_box.append(self.action_editor)