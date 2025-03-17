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
                 can_reset: bool = False,
                 auto_add: bool = True,
                 on_change: callable = None,
                 title: str = None,
                 subtitle: str = None,
                 show_enable_switch: bool = False,
                 start_expanded: bool = False,
                 ):
        super().__init__(action_base, var_name, default_value, can_reset, auto_add, on_change)

        self._widget: BetterExpander = BetterExpander(
            title=self.get_translation(title),
            subtitle=self.get_translation(subtitle),
            expanded=start_expanded,
            show_enable_switch=show_enable_switch
        )

        self.widget.connect("notify::enable-expansion", self._value_changed)

        self._handle_reset_button_creation()

    def add_row(self, widget: Gtk.Widget):
        if widget.get_parent() is not None:
            self.widget.remove_child(widget)
            widget.unparent()
        self.widget.add_row(widget)

    def _value_changed(self, expander_row: BetterExpander, _):
        self._handle_value_changed(expander_row.get_enable_expansion())

    def set_ui_value(self, value: bool):
        self.widget.set_enable_expansion(value)