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
                 on_change: callable = None,
                 title: str = None,
                 subtitle: str = None):
        super().__init__(action_base, var_name, default_value, can_reset, on_change)

        self.widget: Adw.SwitchRow = Adw.SwitchRow(
            title=self.get_translation(title, title),
            subtitle=self.get_translation(subtitle, subtitle),
            active=default_value
        )

        if self._can_reset:
            self.widget.add_prefix(self._create_reset_button())

        self.widget.connect("notify::active", self._value_changed)

    def _value_changed(self, switch, _):
        self._handle_value_changed(switch.get_active())
    
    def set_ui_value(self, value: bool):
        self.widget.set_active(value)