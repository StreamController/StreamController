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
from src.windows.PageManager.elements.MenuButton import MenuButton
from src.windows.PageManager.elements.PageEditorBase import PageEditorGroup
from src.windows.PageManager.elements.PageEditorParts.AutoChangeGroup import (
    AutoChangeGroup,
    MatchingWindowExpander,
)
from src.windows.PageManager.elements.PageEditorParts.BackgroundGroup import BackgroundGroup
from src.windows.PageManager.elements.PageEditorParts.BrightnessGroup import BrightnessGroup
from src.windows.PageManager.elements.PageEditorParts.DefaultPageGroup import DefaultPageGroup
from src.windows.PageManager.elements.PageEditorParts.NameGroup import NameGroup
from src.windows.PageManager.elements.PageEditorParts.ScreensaverGroup import ScreensaverGroup

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk

if TYPE_CHECKING:
    from src.windows.PageManager.PageManager import PageManager

__all__ = [
    "AutoChangeGroup",
    "BackgroundGroup",
    "BrightnessGroup",
    "DefaultPageGroup",
    "MatchingWindowExpander",
    "NameGroup",
    "PageEditor",
    "PageEditorGroup",
    "ScreensaverGroup",
]


class PageEditor(Adw.NavigationPage):
    def __init__(self, page_manager: "PageManager"):
        super().__init__(title=gl.lm.get("page-manager.page-editor.title"))
        self.page_manager = page_manager
        self.active_page_path: str = None
        self.build()

    def get_page_data(self) -> dict:
        return gl.page_manager.get_page_data(self.active_page_path, use_backup=False)

    def set_page_data(self, data: dict, reload_brightness: bool = True, reload_screensaver: bool = True, reload_background: bool = True, reload_inputs: bool = True):
        gl.page_manager.set_page_data(self.active_page_path, data, reload_brightness=reload_brightness, reload_screensaver=reload_screensaver, reload_background=reload_background, reload_inputs=reload_inputs)

    def build(self):
        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, hexpand=True)
        self.set_child(self.main_box)

        # Header
        self.header = Adw.HeaderBar(show_back_button=False, css_classes=["flat"], show_end_title_buttons=True)
        self.main_box.append(self.header)

        # Menu button
        self.menu_button = MenuButton(self)
        self.header.pack_end(self.menu_button)

        # Main stack - one page for the normal editor and one for the no page info screen
        self.main_stack = Gtk.Stack(hexpand=True, vexpand=True, margin_bottom=20)
        self.main_box.append(self.main_stack)

        # The box for the normal editor
        self.editor_main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, hexpand=True)
        self.main_stack.add_titled(self.editor_main_box, "editor", "Editor")

        # Scrolled window for  the normal editor
        self.scrolled_window = Gtk.ScrolledWindow(hexpand=True, vexpand=True)
        self.editor_main_box.append(self.scrolled_window)

        # Clamp for the scrolled window
        self.clamp = Adw.Clamp(margin_top=40)
        self.scrolled_window.set_child(self.clamp)

        # Box for all widgets in the editor
        self.editor_main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.clamp.set_child(self.editor_main_box)

        # Name group - Used to rename the page
        self.name_group = NameGroup(page_editor=self)
        self.editor_main_box.append(self.name_group)

        # Default page group - Used to configure default page for decks
        self.default_page_group = DefaultPageGroup(page_editor=self)
        self.editor_main_box.append(self.default_page_group)

        # Auto change group - Used to configure automatic page switching
        self.auto_change_group = AutoChangeGroup(page_editor=self)
        self.editor_main_box.append(self.auto_change_group)

        # Brightness Group
        self.brightness_group = BrightnessGroup(page_editor=self)
        self.editor_main_box.append(self.brightness_group)

        # Background Group
        self.background_group = BackgroundGroup(page_editor=self)
        self.editor_main_box.append(self.background_group)

        # Screensaver
        self.screensaver_group = ScreensaverGroup(page_editor=self)
        self.editor_main_box.append(self.screensaver_group)

        # No page page
        self.no_page_box = Gtk.Box(hexpand=True, vexpand=True)
        self.main_stack.add_titled(self.no_page_box, "no-page", "No Page")

        self.no_page_box.append(Gtk.Label(label=gl.lm.get("page-manager.page-editor.no-page-selected"), halign=Gtk.Align.CENTER, valign=Gtk.Align.CENTER, hexpand=True))

        # Default to the no page info screen
        self.main_stack.set_visible_child_name("no-page")

    def load_for_page(self, page_path: str) -> None:
        self.active_page_path = page_path
        self.name_group.load_for_page(page_path=page_path)
        self.default_page_group.load_for_page(page_path=page_path)
        self.auto_change_group.load_for_page(page_path=page_path)
        self.brightness_group.load_for_page(page_path=page_path)
        self.background_group.load_for_page(page_path=page_path)
        self.screensaver_group.load_for_page(page_path=page_path)

        self.main_stack.set_visible_child_name("editor")
        self.menu_button.set_page_specific_actions_enabled(True)

    def delete_active_page(self) -> None:
        if self.active_page_path is None:
            return
        
        self.page_manager.remove_page_by_path(self.active_page_path)
