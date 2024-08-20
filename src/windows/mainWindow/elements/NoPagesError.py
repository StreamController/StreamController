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
import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, Gio, GLib

# Import own modules
from GtkHelper.GtkHelper import EntryDialog
from src.windows.PageManager.Importer.Importer import Importer
import os

# Import Python modules
from loguru import logger as log

# Import globals
import globals as gl

# Import signals
from src.Signals import Signals

class NoPagesError(Gtk.Box):
    """
    This error gets shown if there are no pages registered/available
    """
    def __init__(self):
        super().__init__(
            orientation=Gtk.Orientation.VERTICAL,
            halign=Gtk.Align.CENTER,
            valign=Gtk.Align.CENTER,
            homogeneous=False,
            hexpand=True, vexpand=True
        )

        self.build()

    def build(self):
        self.no_pages_label = Gtk.Label(label=gl.lm.get("errors.no-page.header"), css_classes=["error-label"])
        self.append(self.no_pages_label)

        self.create_new_button = Gtk.Button(label=gl.lm.get("errors.no-page.create-new"), margin_top=60, css_classes=["text-button", "suggested-action", "pill"],
                                            hexpand=False, margin_start=60, margin_end=60, halign=Gtk.Align.CENTER)
        self.create_new_button.connect("clicked", self.on_create_new)
        self.append(self.create_new_button)

        self.import_button = Gtk.Button(label=gl.lm.get("errors.no-page.import"), margin_top=10, halign=Gtk.Align.CENTER,
                                        margin_start=60, margin_end=60)
        self.import_button.connect("clicked", self.on_import_clicked)
        self.append(self.import_button)

    def on_create_new(self, button):
        dial = EntryDialog(parent_window=gl.app.main_win,
                           dialog_title=gl.lm.get("page-manager.page-selector.add-dialog.title"),
                           placeholder=gl.lm.get("page-manager.page-selector.add-dialog.placeholder"),
                           confirm_label=gl.lm.get("page-manager.page-selector.add-dialog.confirm"),
                           cancel_label=gl.lm.get("page-manager.page-selector.add-dialog.cancel"),
                           empty_warning=gl.lm.get("page-manager.page-selector.add-dialog.empty-warning"),
                           already_exists_warning=gl.lm.get("page-manager.page-selector.add-dialog.already-exists-warning"),
                           forbid_answers=gl.page_manager.get_page_names())
        dial.show(self.add_page_callback)

    def add_page_callback(self, name:str):
        path = os.path.join(gl.CONFIG_PATH, "pages", f"{name}.json")
        gl.page_manager.add_page(name)

        # Notify plugin actions
        gl.signal_manager.trigger_signal(Signals.PageAdd, path)

        gl.app.main_win.check_for_errors()

        visible_child = gl.app.main_win.leftArea.deck_stack.get_visible_child()
        if visible_child is None:
            return
        active_controller = visible_child.deck_controller
        if active_controller is None:
            return
        
        active_controller.load_default_page()

    def on_import_clicked(self, button):
        popover = Popover(parent=self)
        popover.popup()

class Popover(Gtk.PopoverMenu):
    def __init__(self, parent: Gtk.Widget):
        super().__init__(has_arrow=False)
        self.set_parent(parent)

        self.action_group = Gio.SimpleActionGroup()
        self.insert_action_group("import", self.action_group)

        self.streamdeck_ui_action = Gio.SimpleAction.new("streamdeck-ui", None)
        self.streamdeck_ui_action.connect("activate", self.on_import_streamdeck_ui)

        self.action_group.add_action(self.streamdeck_ui_action)

        self.menu = Gio.Menu.new()
        self.menu.append("StreamDeck UI", "import.streamdeck-ui")
        self.set_menu_model(self.menu)

    def on_import_streamdeck_ui(self, *args):
        ChooseFileDialog(self, self.streamdeck_ui_callback)

    def streamdeck_ui_callback(self, selected_file):
        importer = Importer(gl.app, window=gl.app.main_win)
        # GLib.idle_add(importer.present)
        importer.present()
        importer.import_pages(selected_file.get_path(), "streamdeck-ui", gl.app.main_win.check_for_errors)

class ChooseFileDialog(Gtk.FileDialog):
    def __init__(self, menu_button: Gtk.MenuButton, callback: callable = None):
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
