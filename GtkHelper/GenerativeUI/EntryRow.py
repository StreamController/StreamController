from GtkHelper.GenerativeUI.GenerativeUI import GenerativeUI

import gi
from gi.repository import Gtk, Adw, GLib

from typing import TYPE_CHECKING, Callable
from GtkHelper.GtkHelper import better_disconnect

if TYPE_CHECKING:
    from src.backend.PluginManager import ActionBase

class EntryRow(GenerativeUI[str]):
    def __init__(self, action_base: "ActionBase",
                 var_name: str,
                 default_value: str,
                 title: str = None,
                 filter_func: Callable[[str], str] = None,
                 on_change: callable = None,
                 can_reset: bool = True,
                 auto_add: bool = True,
                 ):
        super().__init__(action_base, var_name, default_value, can_reset, auto_add, on_change)

        self._widget: Adw.EntryRow = Adw.EntryRow(
            title=self.get_translation(title, title),
            text=self._default_value
        )

        self.filter_func = filter_func

        self._handle_reset_button_creation()

        self.widget.connect("changed", self._value_changed)

    def _text_reset(self, text):
        better_disconnect(self.widget, self._value_changed)

        cursor_pos = self.widget.get_position()
        text_is_filtered = text != self.widget.get_text()

        self.set_ui_value(text)

        if text_is_filtered:
            self.widget.set_position(cursor_pos-1)
        else:
            self.widget.set_position(cursor_pos)

        self.widget.connect("changed", self._value_changed)

    def _value_changed(self, entry_row: Adw.EntryRow):
        text = entry_row.get_text()

        if self.filter_func is not None:
            text = self.filter_func(text)

        GLib.idle_add(self._text_reset, text)
        self._handle_value_changed(text)

    def set_ui_value(self, value: str):
        self.widget.set_text(value)