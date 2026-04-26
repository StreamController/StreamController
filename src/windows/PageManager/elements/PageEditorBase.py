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

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw

if TYPE_CHECKING:
    from src.windows.PageManager.elements.PageEditor import PageEditor


class PageEditorGroup(Adw.PreferencesGroup):
    def __init__(self, page_editor: "PageEditor", *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.page_editor = page_editor
        self.build()

    def build(self):
        pass

    def connect_events(self):
        pass

    def disconnect_events(self):
        pass

    def load_config_settings(self, page_path: str):
        pass

    def load_for_page(self, page_path: str) -> None:
        self.disconnect_events()
        self.load_config_settings(page_path)
        self.connect_events()
