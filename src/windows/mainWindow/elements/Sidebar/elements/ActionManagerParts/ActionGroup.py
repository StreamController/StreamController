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

from src.backend.DeckManagement.InputIdentifier import InputIdentifier
from src.windows.mainWindow.elements.Sidebar.elements.ActionManagerParts.ActionExpanderRow import (
    ActionExpanderRow,
)

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw


class ActionGroup(Adw.PreferencesGroup):
    def __init__(self, sidebar, **kwargs):
        super().__init__(**kwargs)
        self.sidebar = sidebar
        self.active_identifier = None

        self.actions = []

        self.build()

    def build(self):
        self.expander = ActionExpanderRow(self)
        self.add(self.expander)

    def load_for_identifier(self, identifier: InputIdentifier, state: int):
        self.active_identifier = identifier
        self.expander.load_for_identifier(identifier, state)

    def load_for_coords(self, coords: tuple[int, int], state: int):
        self.expander.load_for_coords(coords, state)

    def load_for_screen(self, gesture: str, state: int):
        self.expander.load_for_screen(gesture, state)

    def load_for_dial(self, n: int, state: int):
        self.expander.load_for_dial(n, state)
