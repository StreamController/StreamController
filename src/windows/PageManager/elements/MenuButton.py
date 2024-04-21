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

from GtkHelper.GtkHelper import EntryDialog

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, Gio, GLib

import globals as gl
import json
import os

from loguru import logger as log 
from src.windows.PageManager.Importer.Importer import Importer
# Import typing
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from src.windows.PageManager.elements.PageEditor import PageEditor

# Import signals
from src.Signals import Signals

class MenuButton(Gtk.MenuButton):
    def __init__(self, pageEditor: "PageEditor"):
        super().__init__()
        self.pageEditor = pageEditor
        self.set_icon_name("open-menu-symbolic")

        self.selected_file: str = None

        self.init_actions()
        self.set_page_specific_actions_enabled(False)
        self.build()

    def init_actions(self):
        self.action_group = Gio.SimpleActionGroup()
        self.insert_action_group("pm", self.action_group)

        self.import_streamdeck_ui_action = Gio.SimpleAction.new("streamdeck-ui", None)
        self.duplicate_page_action = Gio.SimpleAction.new("duplicate-page", None)
        self.export_page_action = Gio.SimpleAction.new("export-page", None)
        self.import_page_action = Gio.SimpleAction.new("import-page", None)

        self.duplicate_page_action.connect("activate", self.on_duplicate_page)
        self.import_streamdeck_ui_action.connect("activate", self.on_import_streamdeck_ui)
        self.export_page_action.connect("activate", self.on_export_page)
        self.import_page_action.connect("activate", self.on_import_page)

        self.action_group.add_action(self.duplicate_page_action)
        self.action_group.add_action(self.import_streamdeck_ui_action)
        self.action_group.add_action(self.export_page_action)
        self.action_group.add_action(self.import_page_action)

    def set_page_specific_actions_enabled(self, enabled: bool):
        self.duplicate_page_action.set_enabled(enabled)
        self.export_page_action.set_enabled(enabled)

    def build(self):
        self.menu = Gio.Menu.new()
        self.menu.append(gl.lm.get("page-manager.duplicate"), "pm.duplicate-page")
        self.menu.append(gl.lm.get("page-manager.export-page"), "pm.export-page")

        self.import_menu = Gio.Menu.new()
        self.menu.append_submenu(gl.lm.get("page-manager.import"), self.import_menu)

        self.import_menu.append(gl.lm.get("page-manager.import.page"), "pm.import-page")
        self.import_menu.append("StreamDeck UI", "pm.streamdeck-ui")


        # Popover
        self.popover = Gtk.PopoverMenu()
        self.popover.set_menu_model(self.menu)
        self.set_popover(self.popover)

    def on_import_streamdeck_ui(self, *args):
        ChooseImportFileDialog(self, self.streamdeck_ui_callback)

    def streamdeck_ui_callback(self, selected_file):
        importer = Importer(gl.app, self.pageEditor.page_manager)
        # GLib.idle_add(importer.present)
        importer.present()
        importer.import_pages(selected_file.get_path(), "streamdeck-ui")

    def on_export_page(self, *args):
        path = self.pageEditor.active_page_path
        if path in [None, ""]:
            return
        
        initial_name = os.path.basename(path)
        ChooseExportFileDialog(self, self.export_page_callback, initial_name=initial_name)

    def export_page_callback(self, selected_file):
        page_json = {}
        with open(self.pageEditor.active_page_path, "r") as f:
            page_json = json.load(f)

        with open(selected_file.get_path(), "w") as f:
            json.dump(page_json, f, indent=4)

    def on_import_page(self, *args):
        ChooseImportFileDialog(self, self.import_page_callback)

    def import_page_callback(self, selected_file):
        if selected_file in [None, ""]:
            return
        page_name = os.path.splitext(os.path.basename(selected_file.get_path()))[0]
        self.selected_file = selected_file
        if page_name in gl.page_manager.get_page_names():
            dial = EntryDialog(parent_window=self.pageEditor.page_manager,
                           dialog_title=gl.lm.get("page-manager.page-selector.add-dialog.title"),
                           placeholder=gl.lm.get("page-manager.page-selector.add-dialog.placeholder"),
                           confirm_label=gl.lm.get("page-manager.page-selector.add-dialog.confirm"),
                           cancel_label=gl.lm.get("page-manager.page-selector.add-dialog.cancel"),
                           empty_warning=gl.lm.get("page-manager.page-selector.add-dialog.empty-warning"),
                           already_exists_warning=gl.lm.get("page-manager.page-selector.add-dialog.already-exists-warning"),
                           forbid_answers=gl.page_manager.get_page_names(),
                           default_text=page_name)
        
            dial.show(callback_func=self.import_page_name_selected_callback)
        else:
            self.import_page_name_selected_callback(page_name)


    def import_page_name_selected_callback(self, name):
        page_path = os.path.join(gl.DATA_PATH, "pages", f"{name}.json")
        if os.path.exists(page_path):
            return
        
        import_dict = {}
        with open(self.selected_file.get_path(), "r") as f:
            import_dict = json.load(f)

        self.selected_file = None

        page_name = os.path.splitext(os.path.basename(page_path))[0]
        gl.page_manager.add_page(page_name, import_dict)

        self.pageEditor.page_manager.page_selector.add_row_by_path(page_path)

        # Emit signal
        gl.signal_manager.trigger_signal(Signals.PageAdd, page_path)

    def on_duplicate_page(self, *args):
        active_page_path = self.pageEditor.active_page_path
        if active_page_path in [None, ""]:
            return
        
        file =Gio.File.new_for_path(active_page_path)
        self.import_page_callback(file)

        

class ChooseImportFileDialog(Gtk.FileDialog):
    def __init__(self, menu_button: MenuButton, callback: callable = None):
        super().__init__(title=gl.lm.get("asset-chooser.custom.browse-files.dialog.title"),
                         accept_label=gl.lm.get("asset-chooser.custom.browse-files.dialog.select-button"))
        self.menu_button = menu_button
        self.original_callback = callback
        self.open(callback=self.callback)

    def callback(self, dialog, result):
        try:
            selected_file = self.open_finish(result)
        except GLib.Error as err:
            log.error(err)
            return
        
        self.original_callback(selected_file)

class ChooseExportFileDialog(Gtk.FileDialog):
    def __init__(self, menu_button: MenuButton, callback: callable = None, initial_name: str = None):
        super().__init__(title=gl.lm.get("asset-chooser.custom.browse-files.dialog.title"),
                         accept_label=gl.lm.get("asset-chooser.custom.browse-files.dialog.select-button"),
                         initial_name=initial_name)
        self.menu_button = menu_button
        self.original_callback = callback
        self.save(callback=self.callback)

    def callback(self, dialog, result):
        try:
            selected_file = self.save_finish(result)
        except GLib.Error as err:
            log.error(err)
            return
        
        self.original_callback(selected_file)