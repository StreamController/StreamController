from GtkHelper.GenerativeUI.GenerativeUI import GenerativeUI

import gi
import base64
from gi.repository import Gtk, Adw

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from src.backend.PluginManager import ActionBase

class PasswordEntryRow(GenerativeUI[str]):
    def __init__(self, action_base: "ActionBase",
                 var_name: str,
                 default_value: str,
                 on_change: callable = None,
                 title: str = None):
        super().__init__(action_base, var_name, default_value, on_change)

        self.widget: Adw.PasswordEntryRow = Adw.PasswordEntryRow(
            title=self.get_translation(title, title),
            text=self._default_value
        )
        self.widget.connect("changed", self._value_changed)

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

    def set_ui_value(self, value: str):
        self.widget.set_text(value)