from dataclasses import dataclass

from GtkHelper.GenerativeUI.GenerativeUI import GenerativeUI
from GtkHelper.FileDialogRow import FileDialogRow as FileDialog, FileDialogFilter

import gi
from gi.repository import Gtk, Adw, Gio, Gdk

from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from src.backend.PluginManager import ActionBase



class FileDialogRow(GenerativeUI[str]):
    def __init__(self, action_base: "ActionBase",
                 var_name: str,
                 default_value: str,
                 title: str = None,
                 subtitle: str = None,
                 dialog_title: str = None,
                 block_interaction: bool = True,
                 only_show_filename: bool = True,
                 filters: list[FileDialogFilter] = None,
                 on_change: callable = None,
                 can_reset: bool = True,
                 auto_add: bool = True,
                 ):
        super().__init__(action_base, var_name, default_value, can_reset, auto_add, on_change)

        self._widget: FileDialog = FileDialog(
            title=self.get_translation(title),
            subtitle=self.get_translation(subtitle),
            dialog_title=self.get_translation(dialog_title),
            initial_path=default_value,
            block_interaction=block_interaction,
            only_show_filename=only_show_filename,
            filters=filters,
            file_change_callback=self._file_changed
        )

        self._handle_reset_button_creation()

    def set_file(self, path: str, update_setting: bool = False):
        self.set_ui_value(path)

        if update_setting:
            self.set_value(path)

    def get_file(self)-> Gio.File:
        return self.widget.selected_file

    def _file_changed(self, file: Gio.File):
        self._handle_value_changed(file.get_path())

    @GenerativeUI.signal_manager
    def set_ui_value(self, value: str):
        self.widget.load_from_path(value)