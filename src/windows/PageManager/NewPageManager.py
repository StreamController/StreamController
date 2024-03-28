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
# Import gtk modules
import os
import gi

from GtkHelper.GtkHelper import BetterExpander
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, Gio

# Import globals
import globals as gl

class PageManager(Adw.ApplicationWindow):
    def __init__(self, app:"App"):
        super().__init__(title=gl.lm.get("page-manager.title"), default_width=400, default_height=600)
        self.set_transient_for(app.main_win)

        self.build()

        self.page_selector.load_pages()




    def build(self):
        # Split view
        self.split = Adw.NavigationSplitView(vexpand=True)
        self.set_content(self.split)

        self.page_editor = PageEditor(self)
        self.split.set_content(self.page_editor)

        self.page_selector = PageSelector(self)
        self.split.set_sidebar(self.page_selector)




class PageSelector(Adw.NavigationPage):
    def __init__(self, page_manager: PageManager):
        super().__init__(title="Page Selector")
        self.page_manager = page_manager
        self.page_rows: list[PageRow] = []
        self.build()

        self.list_box.select_row(None)

    def build(self):
        self.scrolled_window = Gtk.ScrolledWindow(hexpand=True, vexpand=True)
        self.set_child(self.scrolled_window)

        self.clamp = Adw.Clamp()
        self.scrolled_window.set_child(self.clamp)

        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.clamp.set_child(self.main_box)

        self.list_box = Gtk.ListBox(css_classes=["navigation-sidebar"], selection_mode=Gtk.SelectionMode.SINGLE)
        self.list_box.connect("row-selected", self.on_row_activated)
        self.main_box.append(self.list_box)

    def load_pages(self) -> None:
        self.page_rows.clear()
        pages = gl.page_manager.get_pages()
        for page_path in pages:
            page_row = PageRow(page_manager=self, page_path=page_path)
            self.page_rows.append(page_row)
            self.list_box.append(page_row)

    def on_row_activated(self, list_box: Gtk.ListBox, row: "PageRow") -> None:
        self.page_manager.page_editor.load_for_page(row.page_path)

    def rename_page_row(self, old_path: str, new_path: str) -> None:
        for page_row in self.page_rows:
            if page_row.page_path == old_path:
                page_row.set_page_path(new_path)


class PageRow(Gtk.ListBoxRow):
    def __init__(self, page_manager: PageManager, page_path: str):
        super().__init__()
        self.page_manager = page_manager
        self.page_path = page_path
        self.build()

    def build(self):
        self.main_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, hexpand=True)
        self.set_child(self.main_box)

        self.label = Gtk.Label(label="", hexpand=True, xalign=0)
        self.set_page_path(self.page_path)
        self.main_box.append(self.label)

        self.menu_button = Gtk.Button(icon_name="open-menu-symbolic", halign=Gtk.Align.END, css_classes=["flat"])
        self.main_box.append(self.menu_button)
    
    def set_page_path(self, page_path: str) -> None:
        self.page_path = page_path
        self.label.set_text(os.path.splitext(os.path.basename(self.page_path))[0])


class PageEditor(Adw.NavigationPage):
    def __init__(self, page_manager: PageManager):
        super().__init__(title="Page Editor")
        self.page_manager = page_manager
        self.active_page_path: str = None
        self.build()

    def build(self):
        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, hexpand=True)
        self.set_child(self.main_box)

        # Header
        self.header = Adw.HeaderBar(show_back_button=False, css_classes=["flat"])
        self.main_box.append(self.header)

        self.scrolled_window = Gtk.ScrolledWindow(hexpand=True, vexpand=True)
        self.main_box.append(self.scrolled_window)

        self.clamp = Adw.Clamp(margin_top=40)
        self.scrolled_window.set_child(self.clamp)

        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.clamp.set_child(self.main_box)

        self.name_group = NameGroup(page_editor=self)
        self.main_box.append(self.name_group)

        self.auto_change_group = AutoChangeGroup(page_editor=self)
        self.main_box.append(self.auto_change_group)

    def load_for_page(self, page_path: str) -> None:
        self.active_page_path = page_path
        self.name_group.load_for_page(page_path=page_path)


class NameGroup(Adw.PreferencesGroup):
    def __init__(self, page_editor: PageEditor):
        super().__init__(title="Name")
        self.page_editor = page_editor
        self.build()

    def build(self):
        self.name_entry = Adw.EntryRow(title="Name", show_apply_button=True)
        self.name_entry.connect("changed", self.on_name_changed)
        self.name_entry.connect("apply", self.on_name_change_applied)
        self.add(self.name_entry)

    def load_for_page(self, page_path: str) -> None:
        self.name_entry.set_text(os.path.splitext(os.path.basename(page_path))[0])

        base_path = os.path.dirname(page_path)
        is_user_page = base_path == os.path.join(gl.DATA_PATH, "pages")
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

        # gl.page_manager.move_page(original_path, new_path)

        # Update ui
        self.page_editor.page_manager.page_selector.rename_page_row(old_path=original_path, new_path=new_path)



class AutoChangeGroup(Adw.PreferencesGroup):
    def __init__(self, page_editor: PageEditor):
        super().__init__(title="Auto Change")
        self.page_editor = page_editor
        self.build()

    def build(self):
        self.enable_row = Adw.SwitchRow(title="Enable")
        self.add(self.enable_row)

        self.wm_class_entry = Adw.EntryRow(title="WM Class")
        self.add(self.wm_class_entry)

        self.title_entry = Adw.EntryRow(title="Title")
        self.add(self.title_entry)

        windows = [["org.gnome.Nautilus", "Nautilus"]] * 3
        self.matching_windows_expander = MatchingWindowsExpander()
        self.matching_windows_expander.load_windows(windows=windows)
        self.add(self.matching_windows_expander)


class MatchingWindowsExpander(BetterExpander):
    def __init__(self):
        super().__init__(title="Matching Windows", subtitle="Matching Windows", expanded=False)

        self.update_button = Gtk.Button(icon_name="view-refresh-symbolic", valign=Gtk.Align.CENTER, css_classes=["flat"])
        self.add_suffix(self.update_button)

    def load_windows(self, windows: list[list[str, str]]):
        self.clear()
        for wm_class, title in windows:
            self.add_row(Adw.ActionRow(title=title, subtitle=wm_class))
