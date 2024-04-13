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

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, Gio, GLib

import globals as gl

from loguru import logger as log 
from src.windows.PageManager.Importer.Importer import Importer
# Import typing
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from src.windows.PageManager.elements.PageEditor import PageEditor

class MenuButton(Gtk.MenuButton):
    def __init__(self, pageEditor: "PageEditor"):
        super().__init__()
        self.pageEditor = pageEditor
        self.set_icon_name("open-menu-symbolic")

        self.init_actions()
        self.build()

    def init_actions(self):
        self.import_streamdeck_ui_action = Gio.SimpleAction.new("streamdeck-ui", None)
        self.import_streamdeck_ui_action.connect("activate", self.on_import_streamdeck_ui)
        self.pageEditor.page_manager.add_action(self.import_streamdeck_ui_action)


    def build(self):
        self.menu = Gio.Menu.new()

        self.import_menu = Gio.Menu.new()
        self.menu.append_submenu("Import", self.import_menu)

        self.import_menu.append("StreamDeck UI", "win.streamdeck-ui")

        # Popover
        self.popover = Gtk.PopoverMenu()
        self.popover.set_menu_model(self.menu)
        self.set_popover(self.popover)

    def on_import_streamdeck_ui(self, *args):
        ChooseFileDialog(self, self.streamdeck_ui_callback)

    def streamdeck_ui_callback(self, selected_file):
        importer = Importer(gl.app, self.pageEditor.page_manager)
        GLib.idle_add(importer.present)
        importer.import_pages(selected_file.get_path(), "streamdeck-ui")

        self.pageEditor.page_manager.page_selector.load_pages()

class ChooseFileDialog(Gtk.FileDialog):
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