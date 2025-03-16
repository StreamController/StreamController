from GtkHelper.GenerativeUI.GenerativeUI import GenerativeUI

import gi
from gi.repository import Gtk, Adw

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.backend.PluginManager import ActionBase

from GtkHelper.ScaleRow import ScaleRow as Scale

class ScaleRow(GenerativeUI[float]):
    def __init__(self, action_base: "ActionBase",
                 var_name: str,
                 default_value: float,
                 min: float,
                 max: float,
                 add_text_entry: bool = False,
                 can_reset: bool = True,
                 on_change: callable = None,
                 title: str = None,
                 subtitle: str = None,
                 step: float = 0.1,
                 digits: int = 2,
                 draw_value: bool = True,
                 round_digits: bool = True,
                 text_entry_max_length: int = 6,
                 ):
        super().__init__(action_base, var_name, default_value, can_reset, on_change)

        self.widget: Scale = Scale(
            title=self.get_translation(title, title),
            subtitle=self.get_translation(subtitle, subtitle),
            value=self._default_value,
            min=min,
            max=max,
            add_text_entry=add_text_entry,
            step=step,
            digits=digits,
            draw_value=draw_value,
            round_digits=round_digits,
            text_entry_max_length=text_entry_max_length,
        )

        self._handle_reset_button_creation()

        self.widget.scale.connect("value-changed", self._value_changed)

    def _value_changed(self, scale):
        self._handle_value_changed(scale.get_value())

    def set_ui_value(self, value: float):
        self.widget.scale.set_value(value)

    def set_min(self, min: float):
        self.widget.set_min(min)

    def set_max(self, max: float):
        self.widget.set_max(max)

    def set_step(self, step: float):
        self.widget.set_step(step)