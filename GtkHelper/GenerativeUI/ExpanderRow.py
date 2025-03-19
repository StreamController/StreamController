from functools import partial

from GtkHelper.GenerativeUI.GenerativeUI import GenerativeUI

import gi
from gi.repository import Gtk, Adw, GLib

from typing import TYPE_CHECKING, Callable
from GtkHelper.GtkHelper import better_disconnect

if TYPE_CHECKING:
    from src.backend.PluginManager import ActionBase

from GtkHelper.GtkHelper import BetterExpander

class ExpanderRow(GenerativeUI[bool]):
    def __init__(self, action_base: "ActionBase",
                 var_name: str,
                 default_value: bool,
                 title: str = None,
                 subtitle: str = None,
                 show_enable_switch: bool = False,
                 start_expanded: bool = False,
                 on_change: callable = None,
                 can_reset: bool = False,
                 auto_add: bool = True,
                 ):
        super().__init__(action_base, var_name, default_value, can_reset, auto_add, on_change)

        self._widget: BetterExpander = BetterExpander(
            title=self.get_translation(title),
            subtitle=self.get_translation(subtitle),
            expanded=start_expanded,
            show_enable_switch=show_enable_switch
        )
        self._handle_reset_button_creation()
        self.connect_signals()

    def connect_signals(self):
        self.widget.connect("notify::enable-expansion", self._value_changed)

    def disconnect_signals(self):
        better_disconnect(self.widget, self._value_changed)

    def set_enable_expansion(self, enable_expansion: bool, update_setting: bool = False):
        self.set_ui_value(enable_expansion)

        if update_setting:
            self.set_value(enable_expansion)

    def get_enable_expansion(self) -> bool:
        return self.widget.get_enable_expansion()

    def add_row(self, widget: Gtk.Widget):
        if widget.get_parent() is not None:
            self.widget.remove_child(widget)
            widget.unparent()
        self.widget.add_row(widget)

    def _value_changed(self, expander_row: BetterExpander, _):
        self._handle_value_changed(expander_row.get_enable_expansion())

    @GenerativeUI.signal_manager
    def set_ui_value(self, value: bool):
        self.widget.set_enable_expansion(value)

    @property
    def expanded(self):
        return self.widget.get_expanded()

    @expanded.setter
    def expanded(self, value):
        self.widget.set_expanded(value)