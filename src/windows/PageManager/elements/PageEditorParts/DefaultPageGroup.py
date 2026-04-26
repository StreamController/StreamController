"""
Author: Core447
Year: 2024

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
any later version.

This programm comes with ABSOLUTELY NO WARRANTY!

You should have received a copy of the GNU General Public License
along with this program. If not, see <https://www.gnu.org/licenses/>.
"""
from typing import TYPE_CHECKING

import gi

import globals as gl
from src.windows.MultiDeckSelector.MultiDeckSelectorRow import MultiDeckSelectorRow
from src.windows.PageManager.elements.PageEditorBase import PageEditorGroup

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

if TYPE_CHECKING:
    from src.windows.PageManager.elements.PageEditor import PageEditor


class DefaultPageGroup(PageEditorGroup):
    def __init__(self, page_editor: "PageEditor"):
        super().__init__(page_editor, title=gl.lm.get("page-manager.page-editor.default-page.title"))

    def build(self):
        self.deck_selector = MultiDeckSelectorRow(
            source_window=self.page_editor.page_manager,
            title=gl.lm.get("page-manager.page-editor.default-page.row.title"),
            subtitle=gl.lm.get("page-manager.page-editor.default-page.row.subtitle"),
            callback=self.on_deck_changed,
            selected_deck_serials=gl.page_manager.get_serial_numbers_from_page(self.page_editor.active_page_path)
        )
        self.add(self.deck_selector)

    def load_config_settings(self, page_path: str):
        serial_numbers = gl.page_manager.get_serial_numbers_from_page(page_path)

        self.deck_selector.set_label(len(serial_numbers))
        self.deck_selector.set_selected_deck_serials(serial_numbers)

    def on_deck_changed(self, serial_number: str, state: bool):
        path = self.page_editor.active_page_path

        if not state:
            path = None

        gl.page_manager.set_default_page(serial_number, path)
