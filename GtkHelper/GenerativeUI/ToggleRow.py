from GtkHelper.GenerativeUI.GenerativeUI import GenerativeUI

import gi
from gi.repository import Gtk, Adw

from typing import TYPE_CHECKING

from GtkHelper.GtkHelper import better_disconnect

from GtkHelper.ToggleRow import ToggleRow as Toggle

if TYPE_CHECKING:
    from src.backend.PluginManager.ActionCore import ActionCore

class ToggleRow(GenerativeUI[bool]):
    def __init__(self, action_core: "ActionCore",
                 var_name: str,
                 default_value: int,
                 toggles: list[Adw.Toggle] = None,
                 title: str = None,
                 subtitle: str = None,
                 can_shrink: bool = True,
                 homogeneous: bool = True,
                 active: bool = True,
                 on_change: callable = None,
                 can_reset: bool = True,
                 auto_add: bool = True,
                 complex_var_name: bool = False
                 ):
        super().__init__(action_core, var_name, default_value, can_reset, auto_add, complex_var_name, on_change)

        self._widget: Toggle = Toggle(
            toggles = toggles,
            active_toggle = self._default_value,
            title=self.get_translation(title),
            subtitle=self.get_translation(subtitle),
            can_shrink=can_shrink,
            homogeneous=homogeneous,
            active=active
        )

        self._handle_reset_button_creation()
        self.connect_signals()



    def _handle_value_changed(self, new_value, update_settings: bool = True, trigger_callback: bool = True):
        old_value = self.get_value()

        if update_settings:
            self.set_value(new_value)

        if trigger_callback and self.on_change:
            new_toggle = self._widget.get_toggle_at(new_value)
            old_toggle = self._widget.get_toggle_at(old_value)

            self.on_change(self.widget, new_toggle, old_toggle)

    def connect_signals(self):
        self.widget.toggle_group.connect("notify::active", self._value_changed)

    def disconnect_signals(self):
        better_disconnect(self.widget.toggle_group, self._value_changed)

    def _value_changed(self, toggle_group, _):
        index = self.widget.get_active_index()
        self._handle_value_changed(index)

    @GenerativeUI.signal_manager
    def set_ui_value(self, value: int):
        self.widget.set_active_toggle(value)

    def reset_value(self):
        self.widget.set_active_toggle(self._default_value)
        self._handle_value_changed(self._default_value)