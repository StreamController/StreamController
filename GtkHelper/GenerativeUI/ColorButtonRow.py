from dataclasses import dataclass

from GtkHelper.GenerativeUI.GenerativeUI import GenerativeUI
from GtkHelper.ColorButtonRow import ColorButtonRow as ColorDialog

import gi
from gi.repository import Gtk, Adw, Gio

from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from src.backend.PluginManager import ActionBase



class ColorButtonRow(GenerativeUI[tuple[int, int, int, int]]):
    def __init__(self,
                 action_base: "ActionBase",
                 var_name: str,
                 default_value: tuple[int, int, int, int],
                 title: str = None,
                 subtitle: str = None,
                 on_change: callable = None,
                 can_reset: bool = True,
                 auto_add: bool = True,
                 ):
        super().__init__(action_base, var_name, default_value, can_reset, auto_add, on_change)

        self._widget: ColorDialog = ColorDialog(
            title=self.get_translation(title),
            subtitle=self.get_translation(subtitle),
            default_color=self._default_value
        )

        self._handle_reset_button_creation()

        self.widget.color_button.connect("color-set", self._value_changed)

    def _value_changed(self, button: Gtk.ColorButton):
        color = self.widget.get_color()
        self._handle_value_changed(color)

    def set_ui_value(self, value: tuple[int, int, int, int]):
        self.widget.set_color(value)