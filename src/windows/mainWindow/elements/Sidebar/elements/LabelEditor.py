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
import gi

from src.backend.DeckManagement.DeckController import KeyLabel
from src.backend.DeckManagement.InputIdentifier import InputIdentifier
from src.windows.mainWindow.elements.Sidebar.elements.LabelEditorParts.LabelExpanderRow import (
    LabelExpanderRow,
)
from src.windows.mainWindow.elements.Sidebar.elements.LabelEditorParts.LabelGroup import (
    LabelGroup,
)
from src.windows.mainWindow.elements.Sidebar.elements.LabelEditorParts.LabelRow import LabelRow
from src.windows.mainWindow.elements.Sidebar.elements.LabelEditorParts.widgets import (
    AlignmentButtons,
    ColorChooserButton,
    FontChooserButton,
    SpinButton,
    TextEntry,
)

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk

__all__ = [
    "AlignmentButtons",
    "ColorChooserButton",
    "FontChooserButton",
    "LabelEditor",
    "LabelExpanderRow",
    "LabelGroup",
    "LabelRow",
    "SpinButton",
    "TextEntry",
]


class LabelEditor(Gtk.Box):
    def __init__(self, sidebar, **kwargs):
        self.sidebar = sidebar
        super().__init__(**kwargs)
        self.build()

    def build(self):
        self.clamp = Adw.Clamp()
        self.append(self.clamp)

        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, hexpand=True)
        self.clamp.set_child(self.main_box)

        self.label_group = LabelGroup(self.sidebar)
        self.main_box.append(self.label_group)

    def load_for_identifier(self, identifier: InputIdentifier, state: int):
        self.label_group.load_for_identifier(identifier, state)
