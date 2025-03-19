from GtkHelper.GenerativeUI.GenerativeUI import GenerativeUI

import gi
from gi.repository import Gtk, Adw

from typing import TYPE_CHECKING

from GtkHelper.GtkHelper import better_disconnect

if TYPE_CHECKING:
    from src.backend.PluginManager import ActionBase

class SwitchRow(GenerativeUI[bool]):
    def __init__(self, action_base: "ActionBase",
                 var_name: str,
                 default_value: bool,
                 title: str = None,
                 subtitle: str = None,
                 on_change: callable = None,
                 can_reset: bool = True,
                 auto_add: bool = True,
                 ):
        super().__init__(action_base, var_name, default_value, can_reset, auto_add, on_change)

        self._widget: Adw.SwitchRow = Adw.SwitchRow(
            title=self.get_translation(title, title),
            subtitle=self.get_translation(subtitle, subtitle),
            active=default_value
        )

        self._handle_reset_button_creation()
        self.connect_signals()

    def connect_signals(self):
        self.widget.connect("notify::active", self._value_changed)

    def disconnect_signals(self):
        better_disconnect(self.widget, self._value_changed)

    def set_active(self, active: bool, change_setting: bool = False):
        self.set_ui_value(active)

        if change_setting:
            self.set_value(active)

    def get_active(self) -> bool:
        return self.widget.get_active()

    def _value_changed(self, switch, _):
        self._handle_value_changed(switch.get_active())

    @GenerativeUI.signal_manager
    def set_ui_value(self, value: bool):
        self.widget.set_active(value)