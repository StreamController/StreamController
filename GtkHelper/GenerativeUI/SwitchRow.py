from GtkHelper.GenerativeUI.GenerativeUI import GenerativeUI

import gi
from gi.repository import Gtk, Adw

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from src.backend.PluginManager import ActionBase

class SwitchRow(GenerativeUI[bool]):
    def __init__(self, action_base: "ActionBase",
                 var_name: str,
                 default_value: bool,
                 can_reset: bool = True,
                 auto_add: bool = True,
                 on_change: callable = None,
                 title: str = None,
                 subtitle: str = None):
        super().__init__(action_base, var_name, default_value, can_reset, auto_add, on_change)

        self._widget: Adw.SwitchRow = Adw.SwitchRow(
            title=self.get_translation(title, title),
            subtitle=self.get_translation(subtitle, subtitle),
            active=default_value
        )

        self._handle_reset_button_creation()

        self.widget.connect("notify::active", self._value_changed)

    def _value_changed(self, switch, _):
        self._handle_value_changed(switch.get_active())
    
    def set_ui_value(self, value: bool):
        self.widget.set_active(value)