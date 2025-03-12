from GtkHelper.GenerativeUI.GenerativeUI import GenerativeUI

import gi
from gi.repository import Gtk, Adw

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from src.backend.PluginManager import ActionCore

class ToggleRow(GenerativeUI[bool]):
    def __init__(self, action_core: "ActionCore", var_name: str, default_value: bool, on_change: callable = None, title: str = None, subtitle: str = None):
        super().__init__(action_core, var_name, default_value, on_change)

        self.widget = Adw.SwitchRow(
            title=title,
            subtitle=subtitle,
            active=default_value
        )
        self.widget.connect("notify::active", self._value_changed)

    def _value_changed(self, switch, _):
        self._handle_value_changed(switch.get_active())

    def get_ui(self) -> Gtk.Widget:
        return self.widget
    
    def set_ui_value(self, value: bool):
        self.widget.set_active(value)