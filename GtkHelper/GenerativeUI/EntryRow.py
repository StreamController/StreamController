from GtkHelper.GenerativeUI.GenerativeUI import GenerativeUI

import gi
from gi.repository import Gtk, Adw

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from src.backend.PluginManager import ActionBase

class EntryRow(GenerativeUI[str]):
    def __init__(self, action_base: "ActionBase",
                 var_name: str,
                 default_value: str,
                 on_change: callable = None,
                 title: str = None):
        super().__init__(action_base, var_name, default_value, on_change)

        self.widget: Adw.EntryRow = Adw.EntryRow(
            title=self.get_translation(title, title),
            text=self._default_value
        )
        self.widget.connect("changed", self._value_changed)

    def _value_changed(self, entry_row: Adw.EntryRow):
        self._handle_value_changed(entry_row.get_text())

    def set_ui_value(self, value: str):
        self.widget.set_text(value)