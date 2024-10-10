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
# Import gi
import gi

from src.windows.MultiDeckSelector.MultiDeckSelectorRow import MultiDeckSelectorRow
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, Gio

# Import typing
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from src.windows.PageManager.PageManager import PageManager

# Import globals
import globals as gl

# Import python modules
import os

# Import own modules
from GtkHelper.GtkHelper import BetterExpander
from src.backend.WindowGrabber.Window import Window
from src.windows.PageManager.elements.MenuButton import MenuButton

class PageEditor(Adw.NavigationPage):
    def __init__(self, page_manager: "PageManager"):
        super().__init__(title=gl.lm.get("page-manager.page-editor.title"))
        self.page_manager = page_manager
        self.active_page_path: str = None
        self.build()

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
        self.main_stack = Gtk.Stack(hexpand=True, vexpand=True)
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

        # Auto change group - Used to configure automatic page switching
        self.auto_change_group = AutoChangeGroup(page_editor=self)
        self.editor_main_box.append(self.auto_change_group)

        self.default_page_group = DefaultPageGroup(page_editor=self)
        self.editor_main_box.append(self.default_page_group)

        # Delete button
        self.delete_button = DeleteButton(page_editor=self, margin_top=40)
        self.editor_main_box.append(self.delete_button)

        # No page page
        self.no_page_box = Gtk.Box(hexpand=True, vexpand=True)
        self.main_stack.add_titled(self.no_page_box, "no-page", "No Page")

        self.no_page_box.append(Gtk.Label(label=gl.lm.get("page-manager.page-editor.no-page-selected"), halign=Gtk.Align.CENTER, valign=Gtk.Align.CENTER, hexpand=True))

        # Default to the no page info screen
        self.main_stack.set_visible_child_name("no-page")

    def load_for_page(self, page_path: str) -> None:
        self.active_page_path = page_path
        self.name_group.load_for_page(page_path=page_path)
        self.auto_change_group.load_for_page(page_path=page_path)
        self.default_page_group.load_for_page(page_path=page_path)

    def delete_active_page(self) -> None:
        if self.active_page_path is None:
            return
        
        self.page_manager.remove_page_by_path(self.active_page_path)


class DeleteButton(Gtk.Button):
    def __init__(self, page_editor: PageEditor, *args, **kwargs):
        super().__init__(css_classes=["destructive-action", "tall-button"], hexpand=True, *args, **kwargs)
        self.page_editor = page_editor
        self.set_label(gl.lm.get("page-manager.page-editor.delete-page"))
        self.connect("clicked", self.on_delete_clicked)

    def on_delete_clicked(self, button: Gtk.Button) -> None:
        dialog = DeletePageConfirmationDialog(page_editor=self.page_editor)
        dialog.present()


class DeletePageConfirmationDialog(Adw.MessageDialog):
    def __init__(self, page_editor: PageEditor, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.page_editor = page_editor

        self.set_transient_for(page_editor.page_manager)
        self.set_modal(True)
        self.set_title(gl.lm.get("page-manager.page-editor.delete-page-confirm.title"))
        self.add_response("cancel", gl.lm.get("page-manager.page-editor.delete-page-confirm.cancel"))
        self.add_response("delete", gl.lm.get("page-manager.page-editor.delete-page-confirm.delete"))
        self.set_default_response("cancel")
        self.set_close_response("cancel")
        self.set_response_appearance("delete", Adw.ResponseAppearance.DESTRUCTIVE)

        page_name = os.path.splitext(os.path.basename(self.page_editor.active_page_path))[0]
        self.set_body(f'{gl.lm.get("page-manager.page-editor.delete-page-confirm.body")}"{page_name}"?')

        self.connect("response", self.on_response)

    def on_response(self, dialog: Adw.MessageDialog, response: int) -> None:
        if response == "delete":
            page_path = self.page_editor.active_page_path
            self.page_editor.page_manager.remove_page_by_path(page_path)
        self.destroy()


class NameGroup(Adw.PreferencesGroup):
    def __init__(self, page_editor: PageEditor):
        super().__init__(title=gl.lm.get("page-manager.page-editor.name-group.title"))
        self.page_editor = page_editor
        self.build()

    def build(self):
        self.name_entry = Adw.EntryRow(title=gl.lm.get("page-manager.page-editor.name-group.name"), show_apply_button=True)
        self.name_entry.connect("changed", self.on_name_changed)
        self.name_entry.connect("apply", self.on_name_change_applied)
        self.add(self.name_entry)

    def load_for_page(self, page_path: str) -> None:
        self.name_entry.set_text(os.path.splitext(os.path.basename(page_path))[0])

        base_path = os.path.dirname(page_path)
        is_user_page = base_path == os.path.join(gl.CONFIG_PATH, "pages")
        self.set_sensitive(is_user_page)

    def on_name_changed(self, entry: Adw.EntryRow, *args):
        original_name = os.path.splitext(os.path.basename(self.page_editor.active_page_path))[0]
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

class AutoChangeGroup(Adw.PreferencesGroup):
    def __init__(self, page_editor: PageEditor):
        super().__init__(title=gl.lm.get("page-manager.page-editor.change-group.title"))
        self.page_editor = page_editor
        self.build()
        

    def build(self):
        self.enable_row = Adw.SwitchRow(title=gl.lm.get("page-manager.page-editor.change-group.enable"))
        self.add(self.enable_row)

        self.stay_on_page = Adw.SwitchRow(title="Stay on page", subtitle="Stay on the page until another page matches")
        self.add(self.stay_on_page)

        self.title_entry = Adw.EntryRow(title=gl.lm.get("page-manager.page-editor.change-group.title-regex"), text="", show_apply_button=True)
        self.add(self.title_entry)

        self.wm_class_entry = Adw.EntryRow(title=gl.lm.get("page-manager.page-editor.change-group.wm-class-regex"), text="", show_apply_button=True)
        self.add(self.wm_class_entry)

        self.matching_windows_expander = MatchingWindowsExpander(auto_change_group=self)
        self.add(self.matching_windows_expander)

        self.device_selector = MultiDeckSelectorRow(source_window=self.page_editor.page_manager,
                                                    title="Decks",
                                                    subtitle="Decks on which the page should be loaded",
                                                    callback=self.on_selected_devices_changed)
        self.add(self.device_selector)
        
        self.connect_signals()

        self.load_config_settings()

    def connect_signals(self):
        self.enable_row.connect("notify::active", self.on_filter_apply)
        self.stay_on_page.connect("notify::active", self.on_filter_apply)
        self.wm_class_entry.connect("apply", self.on_filter_apply)
        self.title_entry.connect("apply", self.on_filter_apply)

    def disconnect_signals(self):
        self.enable_row.disconnect_by_func(self.on_filter_apply)
        self.stay_on_page.disconnect_by_func(self.on_filter_apply)
        self.wm_class_entry.disconnect_by_func(self.on_filter_apply)
        self.title_entry.disconnect_by_func(self.on_filter_apply)

    def on_filter_apply(self, entry: Adw.EntryRow, *args):
        self.matching_windows_expander.update_matching_windows()

        auto_change = {
            "enable": self.enable_row.get_active(),
            "wm_class": self.wm_class_entry.get_text(),
            "title": self.title_entry.get_text(),
            "stay_on_page": self.stay_on_page.get_active()
        }
        gl.page_manager.set_auto_change_info_for_page(page_path=self.page_editor.active_page_path,
                                                      info=auto_change)
        
    def on_selected_devices_changed(self, serial_number, state):
        # gl.page_manager.update_auto_change_info()
        info = gl.page_manager.get_auto_change_info_for_page(page_path=self.page_editor.active_page_path)
        decks = info.get("decks", [])
        if state:
            if serial_number in decks:
                return
            decks.append(serial_number)

        else:
            if serial_number not in decks:
                return
            decks.remove(serial_number)

        info["decks"] = decks
        gl.page_manager.set_auto_change_info_for_page(page_path=self.page_editor.active_page_path, info=info)

    def load_config_settings(self):

        if self.page_editor.active_page_path is None:
            return
        
        self.disconnect_signals()

        auto_change = gl.page_manager.get_auto_change_info_for_page(page_path=self.page_editor.active_page_path)

        self.enable_row.set_active(auto_change.get("enable", False))
        self.stay_on_page.set_active(auto_change.get("stay_on_page", True))
        self.wm_class_entry.set_text(auto_change.get("wm_class", ""))
        self.title_entry.set_text(auto_change.get("title", ""))
        self.device_selector.set_selected_deck_serials(auto_change.get("decks", []).copy())

        self.connect_signals()

    def load_for_page(self, page_path: str) -> None:
        self.load_config_settings()
        self.matching_windows_expander.update_matching_windows()


class MatchingWindowsExpander(BetterExpander):
    def __init__(self, auto_change_group: AutoChangeGroup):
        super().__init__(title=gl.lm.get("page-manager.page-editor.matching-windows.title"), subtitle=gl.lm.get("page-manager.page-editor.matching-windows.subtitle"), expanded=False)
        self.auto_change_group = auto_change_group

        self.update_button = Gtk.Button(icon_name="view-refresh-symbolic", valign=Gtk.Align.CENTER, css_classes=["flat"])
        self.update_button.connect("clicked", self.update_matching_windows)
        self.add_suffix(self.update_button)

        self.update_matching_windows()

    def load_windows(self, windows: list[Window]):
        self.clear()
        for window in windows:
            self.add_row(Adw.ActionRow(title=window.title, subtitle=window.wm_class, use_markup=False))
    
    def update_matching_windows(self, *args):
        class_regex = self.auto_change_group.wm_class_entry.get_text()
        title_regex = self.auto_change_group.title_entry.get_text()

        matching_windows = gl.window_grabber.get_all_matching_windows(class_regex=class_regex, title_regex=title_regex)
        self.load_windows(windows=matching_windows)

class DefaultPageGroup(Adw.PreferencesGroup):
    def __init__(self, page_editor: PageEditor):
        super().__init__(title=gl.lm.get("page-manager.page-editor.default-page.title"))
        self.page_editor = page_editor
        self.build()

    def build(self):
        matches = gl.page_manager.get_all_deck_serial_numbers_with_page_as_default(path=self.page_editor.active_page_path)
        self.row = MultiDeckSelectorRow(source_window=self.page_editor.page_manager, title=gl.lm.get("page-manager.page-editor.default-page.row.title"),
                                        subtitle=gl.lm.get("page-manager.page-editor.default-page.row.subtitle"),
                                        callback=self.on_changed, selected_deck_serials=matches.copy())
        self.add(self.row)

    def on_changed(self, serial_number: str, state: bool):
        path = self.page_editor.active_page_path
        if not state:
            path = None
        
        gl.page_manager.set_default_page_for_deck(serial_number=serial_number, path=path)

    def load_for_page(self, page_path: str) -> None:
        self.update()

    def update(self) -> None:
        matches = gl.page_manager.get_all_deck_serial_numbers_with_page_as_default(path=self.page_editor.active_page_path)
        self.row.set_label(len(matches))
        self.row.set_selected_deck_serials(matches)
