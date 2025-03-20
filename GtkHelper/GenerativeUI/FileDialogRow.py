from dataclasses import dataclass

from GtkHelper.GenerativeUI.GenerativeUI import GenerativeUI
from GtkHelper.FileDialogRow import FileDialogRow as FileDialog, FileDialogFilter

import gi
from gi.repository import Gtk, Adw, Gio, Gdk

from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from src.backend.PluginManager import ActionBase

class FileDialogRow(GenerativeUI[str]):
    """
    A class that represents a file dialog row widget that allows the user to select a file
    from the file system. It includes functionality to display a dialog with filters and
    manage the file selection.

    Inherits from `GenerativeUI` to provide generic UI management and functionality.

    Attributes:
        selected_file (Gio.File): The currently selected file in the dialog.
    """

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
                 auto_add: bool = True):
        """
        Initializes the FileDialogRow widget with a file dialog for selecting a file.

        Args:
            action_base (ActionBase): The base action that provides context for this file dialog row.
            var_name (str): The variable name to associate with this file dialog row.
            default_value (str): The initial path to display in the file dialog.
            title (str, optional): The title to display for the file dialog row.
            subtitle (str, optional): The subtitle to display for the file dialog row.
            dialog_title (str, optional): The title of the file dialog window.
            block_interaction (bool, optional): Whether to block interaction while the dialog is open. Defaults to True.
            only_show_filename (bool, optional): Whether to display only the filename in the dialog. Defaults to True.
            filters (list[FileDialogFilter], optional): A list of file dialog filters to apply. Defaults to None.
            on_change (callable, optional): A callback function to call when the file selection changes.
            can_reset (bool, optional): Whether the value can be reset. Defaults to True.
            auto_add (bool, optional): Whether to automatically add this entry to the UI. Defaults to True.
        """
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
        """
        Sets the file path in the file dialog widget and optionally updates the associated setting.

        Args:
            path (str): The file path to set in the file dialog.
            update_setting (bool, optional): If True, updates the setting with the new file path. Defaults to False.
        """
        self.set_ui_value(path)

        if update_setting:
            self.set_value(path)

    def get_file(self) -> Gio.File:
        """
        Retrieves the currently selected file from the file dialog.

        Returns:
            Gio.File: The selected file in the file dialog.
        """
        return self.widget.selected_file

    def _file_changed(self, file: Gio.File):
        """
        Handles the change in file selection in the file dialog.

        This method is called when the user selects a new file. It updates the associated value accordingly.

        Args:
            file (Gio.File): The newly selected file in the file dialog.
        """
        self._handle_value_changed(file.get_path())

    @GenerativeUI.signal_manager
    def set_ui_value(self, value: str):
        """
        Sets the value (file path) in the UI file dialog widget.

        Args:
            value (str): The file path to set in the UI widget.
        """
        self.widget.load_from_path(value)