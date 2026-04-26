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
import os
from typing import TYPE_CHECKING

import gi

import globals as gl
from GtkHelper.GtkHelper import better_disconnect
from src.windows.PageManager.elements.PageEditorBase import PageEditorGroup

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw

if TYPE_CHECKING:
    from src.windows.PageManager.elements.PageEditor import PageEditor


class NameGroup(PageEditorGroup):
    def __init__(self, page_editor: "PageEditor"):
        super().__init__(page_editor)

    def build(self):
        self.name_entry = Adw.EntryRow(title=gl.lm.get("page-manager.page-editor.name-group.name"), show_apply_button=True)
        self.add(self.name_entry)

    def connect_events(self):
        self.name_entry.connect("changed", self.on_name_changed)
        self.name_entry.connect("apply", self.on_name_change_applied)

    def disconnect_events(self):
        better_disconnect(self.name_entry, self.on_name_changed)
        better_disconnect(self.name_entry, self.on_name_change_applied)

    def load_config_settings(self, page_path: str):
        if page_path is None:
            return

        page_name = os.path.basename(page_path).split(".")[0]
        self.name_entry.set_text(page_name)

        base_path = os.path.dirname(page_path)
        is_user_page = base_path == os.path.join(gl.DATA_PATH, "pages")

        self.set_sensitive(is_user_page)

    def on_name_changed(self, entry: Adw.EntryRow, *args):
        original_name = os.path.basename(self.page_editor.active_page_path).split(".")[0]
        new_name = entry.get_text()

        all_page_names = gl.page_manager.get_page_names()
        all_page_names.remove(original_name)
        all_page_names.append("")

        if new_name in all_page_names:
            entry.add_css_class("error")
            entry.set_show_apply_button(False)
        else:
            entry.remove_css_class("error")
            entry.set_show_apply_button(True)

    def on_name_change_applied(self, entry: Adw.EntryRow, *args):
        original_path = self.page_editor.active_page_path
        new_path = os.path.join(os.path.dirname(original_path), f"{entry.get_text()}.json")

        if original_path == new_path:
            return

        self.page_editor.page_manager.rename_page_by_path(original_path, new_path)
