from GtkHelper.GenerativeUI.GenerativeUI import GenerativeUI

import gi
import base64
from gi.repository import Gtk, Adw

from typing import TYPE_CHECKING

from GtkHelper.GtkHelper import better_disconnect

if TYPE_CHECKING:
    from src.backend.PluginManager import ActionBase


class PasswordEntryRow(GenerativeUI[str]):
    """
    A class that represents a password entry row widget, which allows the user to input and manage passwords.
    This widget includes functionality for setting, getting, and securely handling passwords, with encoding for storage.

    Inherits from `GenerativeUI` to provide generic UI management and functionality.

    Attributes:
        password (str): The currently entered password, encoded and decoded as needed for storage.
    """

    def __init__(self, action_base: "ActionBase",
                 var_name: str,
                 default_value: str,
                 title: str = None,
                 on_change: callable = None,
                 can_reset: bool = True,
                 auto_add: bool = True):
        """
        Initializes the PasswordEntryRow widget, setting up the password entry UI component.

        Args:
            action_base (ActionBase): The base action that provides context for this password entry row.
            var_name (str): The variable name to associate with this password entry row.
            default_value (str): The default password value to display in the entry field.
            title (str, optional): The title to display for the password entry row.
            on_change (callable, optional): A callback function to call when the password changes.
            can_reset (bool, optional): Whether the password can be reset. Defaults to True.
            auto_add (bool, optional): Whether to automatically add this entry to the UI. Defaults to True.
        """
        super().__init__(action_base, var_name, default_value, can_reset, auto_add, on_change)

        self._widget: Adw.PasswordEntryRow = Adw.PasswordEntryRow(
            title=self.get_translation(title, title),
            text=self._default_value
        )

        self._handle_reset_button_creation()
        self.connect_signals()

    def connect_signals(self):
        """
        Connects the signal handler for the 'changed' signal to track changes in the password entry.

        This ensures that when the password input changes, the value is handled accordingly.
        """
        self.widget.connect("changed", self._value_changed)

    def disconnect_signals(self):
        """
        Disconnects the signal handler for the 'changed' signal.

        This method prevents further handling of password changes when the widget is no longer in use
        or when the signals should be stopped.
        """
        better_disconnect(self.widget, self._value_changed)

    def set_password(self, password: str, update_setting: bool = False):
        """
        Sets the password in the password entry widget and optionally updates the associated setting.

        Args:
            password (str): The password to set in the entry field.
            update_setting (bool, optional): If True, updates the setting with the new password. Defaults to False.
        """
        self.set_ui_value(password)

        if update_setting:
            self.set_value(password)

    def get_password(self) -> str:
        """
        Retrieves the current password entered in the password entry field.

        Returns:
            str: The current password entered in the widget.
        """
        return self.widget.get_text()

    def _value_changed(self, entry_row: Adw.EntryRow):
        """
        Handles the change in password input in the password entry row.

        This method is triggered when the user changes the password in the entry field,
        updating the associated value accordingly.

        Args:
            entry_row (Adw.EntryRow): The password entry row widget whose value changed.
        """
        self._handle_value_changed(entry_row.get_text())

    def get_value(self, fallback: str = None):
        """
        Retrieves the stored password value, decoding it from base64.

        This method retrieves the encoded password from settings and decodes it to the original string value.

        Args:
            fallback (str, optional): A fallback value to return if no stored value is found. Defaults to None.

        Returns:
            str: The decoded password value.
        """
        value = super().get_value(fallback)
        return base64.b64decode(value).decode("utf-8")

    def set_value(self, new_value: str):
        """
        Encodes and sets the new password value in the settings.

        This method encodes the password to base64 for secure storage and updates the settings with the new value.

        Args:
            new_value (str): The new password to store, encoded in base64.
        """
        settings = self._action_base.get_settings()

        encoded = base64.b64encode(new_value.encode("utf-8")).decode("utf-8")
        settings[self._var_name] = encoded
        self._action_base.set_settings(settings)

    @GenerativeUI.signal_manager
    def set_ui_value(self, value: str):
        """
        Sets the password value in the UI password entry widget.

        Args:
            value (str): The password value to set in the UI widget.
        """
        self.widget.set_text(value)