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

import globals as gl
from src.backend.DeckManagement.InputIdentifier import InputIdentifier
from src.windows.mainWindow.elements.Sidebar.elements.LabelEditorParts.LabelRow import LabelRow

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw


class LabelExpanderRow(Adw.ExpanderRow):
    def __init__(self, label_group):
        super().__init__(title=gl.lm.get("label-editor-header"), subtitle=gl.lm.get("label-editor-expander-subtitle"))
        self.label_group = label_group
        self.active_identifier: InputIdentifier = None
        self.build()

    def build(self):
        self.top_row = LabelRow(gl.lm.get("label-editor-top-name"), 0, self.label_group.sidebar, key_name="top")
        self.center_row = LabelRow(gl.lm.get("label-editor-center-name"), 1, self.label_group.sidebar, key_name="center")
        self.bottom_row = LabelRow(gl.lm.get("label-editor-bottom-name"), 2, self.label_group.sidebar, key_name="bottom")

        self.add_row(self.top_row)
        self.add_row(self.center_row)
        self.add_row(self.bottom_row)

    def load_for_identifier(self, identifier: InputIdentifier, state: int):
        if not isinstance(identifier, InputIdentifier):
            raise TypeError
        self.active_identifier = identifier

        self.top_row.load_for_identifier(identifier, state)
        self.center_row.load_for_identifier(identifier, state)
        self.bottom_row.load_for_identifier(identifier, state)
