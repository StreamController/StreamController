from GtkHelper.GenerativeUI.GenerativeUI import GenerativeUI

import gi
import base64
from gi.repository import Gtk, Adw

from typing import TYPE_CHECKING

from GtkHelper.GtkHelper import better_disconnect

if TYPE_CHECKING:
    from src.backend.PluginManager import ActionBase

class PasswordEntryRow(GenerativeUI[str]):
    def __init__(self, action_base: "ActionBase",
                 var_name: str,
                 default_value: str,
                 title: str = None,
                 on_change: callable = None,
                 can_reset: bool = True,
                 auto_add: bool = True,
                 ):
        super().__init__(action_base, var_name, default_value, can_reset, auto_add, on_change)

        self._widget: Adw.PasswordEntryRow = Adw.PasswordEntryRow(
            title=self.get_translation(title, title),
            text=self._default_value
        )

        self._handle_reset_button_creation()
        self.connect_signals()

    def connect_signals(self):
        self.widget.connect("changed", self._value_changed)

    def disconnect_signals(self):
        better_disconnect(self.widget, self._value_changed)

    def set_password(self, password: str, update_setting: bool = False):
        self.set_ui_value(password)

        if update_setting:
            self.set_value(password)

    def get_password(self) -> str:
        return self.widget.get_text()

    def _value_changed(self, entry_row: Adw.EntryRow):
        self._handle_value_changed(entry_row.get_text())

    def get_value(self, fallback: str = None):
        value = super().get_value(fallback)
        return base64.b64decode(value).decode("utf-8")

    def set_value(self, new_value: str):
        settings = self._action_base.get_settings()

        encoded = base64.b64encode(new_value.encode("utf-8")).decode("utf-8")
        settings[self._var_name] = encoded
        self._action_base.set_settings(settings)

    @GenerativeUI.signal_manager
    def set_ui_value(self, value: str):
        self.widget.set_text(value)