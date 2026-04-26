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
from GtkHelper.GtkHelper import BetterExpander, better_disconnect
from src.backend.WindowGrabber.Window import Window
from src.windows.MultiDeckSelector.MultiDeckSelectorRow import MultiDeckSelectorRow
from src.windows.PageManager.elements.PageEditorBase import PageEditorGroup

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk

if TYPE_CHECKING:
    from src.windows.PageManager.elements.PageEditor import PageEditor


class AutoChangeGroup(PageEditorGroup):
    def __init__(self, page_editor: "PageEditor"):
        super().__init__(page_editor, title=gl.lm.get("page-manager.page-editor.change-group.title"))

    def build(self):
        self.enable_toggle = Adw.SwitchRow(title=gl.lm.get("page-manager.page-editor.change-group.enable"))
        self.add(self.enable_toggle)

        self.stay_on_page_toggle = Adw.SwitchRow(title="Stay on page", subtitle="Stay on the page until another page matches")
        self.add(self.stay_on_page_toggle)

        self.deck_selector = MultiDeckSelectorRow(
            source_window=self.page_editor.page_manager,
            title="Decks",
            subtitle="Decks on which the page should be loaded",
            callback=self.on_deck_changed,
            selected_deck_serials=gl.page_manager.get_serial_numbers_from_page(self.page_editor.active_page_path)
        )
        self.add(self.deck_selector)

        self.title_entry = Adw.EntryRow(title=gl.lm.get("page-manager.page-editor.change-group.title-regex"), text="", show_apply_button=True)
        self.add(self.title_entry)

        self.wm_class_entry = Adw.EntryRow(title=gl.lm.get("page-manager.page-editor.change-group.wm-class-regex"), text="", show_apply_button=True)
        self.add(self.wm_class_entry)

        self.matching_window_expander = MatchingWindowExpander(auto_change_group=self)
        self.add(self.matching_window_expander)

    def connect_events(self):
        self.enable_toggle.connect("notify::active", self.on_enable_changed)
        self.stay_on_page_toggle.connect("notify::active", self.on_stay_on_page_changed)
        self.title_entry.connect("apply", self.on_title_entry_applied)
        self.wm_class_entry.connect("apply", self.on_wm_class_entry_applied)

    def disconnect_events(self):
        better_disconnect(self.enable_toggle, self.on_enable_changed)
        better_disconnect(self.stay_on_page_toggle, self.on_stay_on_page_changed)
        better_disconnect(self.title_entry, self.on_title_entry_applied)
        better_disconnect(self.wm_class_entry, self.on_wm_class_entry_applied)

    def load_config_settings(self, page_path: str):
        auto_change = gl.page_manager.get_auto_change_settings(self.page_editor.active_page_path)

        self.enable_toggle.set_active(auto_change.get("enable", False))
        self.stay_on_page_toggle.set_active(auto_change.get("stay-on-page", True))
        self.wm_class_entry.set_text(auto_change.get("wm-class", ""))
        self.title_entry.set_text(auto_change.get("title", ""))
        self.deck_selector.set_selected_deck_serials(auto_change.get("decks", []).copy())

    def on_enable_changed(self, *args):
        gl.page_manager.overwrite_auto_change_settings(
            path=self.page_editor.active_page_path,
            enable=self.enable_toggle.get_active()
        )

    def on_stay_on_page_changed(self, *args):
        gl.page_manager.overwrite_auto_change_settings(
            path=self.page_editor.active_page_path,
            stay_on_page=self.stay_on_page_toggle.get_active()
        )

    def on_title_entry_applied(self, *args):
        self.matching_window_expander.update_matching_windows()

        gl.page_manager.overwrite_auto_change_settings(
            path=self.page_editor.active_page_path,
            regex_title=self.title_entry.get_text()
        )

    def on_wm_class_entry_applied(self, *args):
        self.matching_window_expander.update_matching_windows()

        gl.page_manager.overwrite_auto_change_settings(
            path=self.page_editor.active_page_path,
            wm_class=self.wm_class_entry.get_text()
        )

    def on_deck_changed(self, serial_number: str, state: bool):
        path = self.page_editor.active_page_path
        info = gl.page_manager.get_auto_change_settings(path)
        decks = info.get("decks", [])

        if state and serial_number not in decks:
            decks.append(serial_number)
        elif not state and serial_number in decks:
            decks.remove(serial_number)
        else:
            return

        gl.page_manager.overwrite_auto_change_settings(path, decks=decks)


class MatchingWindowExpander(BetterExpander):
    def __init__(self, auto_change_group: AutoChangeGroup):
        super().__init__(
            title=gl.lm.get("page-manager.page-editor.matching-windows.title"),
            subtitle=gl.lm.get("page-manager.page-editor.matching-windows.subtitle"),
            expanded=False
        )

        self.auto_change_group = auto_change_group

        self.update_button = Gtk.Button(icon_name="view-refresh-symbolic", valign=Gtk.Align.CENTER,
                                        css_classes=["flat"])
        self.update_button.connect("clicked", self.update_matching_windows)
        self.add_suffix(self.update_button)

    def load_windows(self, windows: list[Window]):
        self.clear()
        for window in windows:
            self.add_row(Adw.ActionRow(title=window.title, subtitle=window.wm_class, use_markup=False))

    def update_matching_windows(self, *args):
        class_regex = self.auto_change_group.wm_class_entry.get_text()
        title_regex = self.auto_change_group.title_entry.get_text()

        matching_windows = gl.window_grabber.get_all_matching_windows(class_regex=class_regex, title_regex=title_regex)
        self.load_windows(windows=matching_windows)
