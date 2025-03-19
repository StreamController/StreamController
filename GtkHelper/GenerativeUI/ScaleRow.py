from GtkHelper.GenerativeUI.GenerativeUI import GenerativeUI

import gi
from gi.repository import Gtk, Adw

from typing import TYPE_CHECKING

from GtkHelper.GtkHelper import better_disconnect

if TYPE_CHECKING:
    from src.backend.PluginManager import ActionBase

from GtkHelper.ScaleRow import ScaleRow as Scale

class ScaleRow(GenerativeUI[float]):
    def __init__(self, action_base: "ActionBase",
                 var_name: str,
                 default_value: float,
                 min: float,
                 max: float,
                 title: str = None,
                 subtitle: str = None,
                 step: float = 0.1,
                 digits: int = 2,
                 draw_value: bool = True,
                 round_digits: bool = True,
                 add_text_entry: bool = False,
                 text_entry_max_length: int = 6,
                 on_change: callable = None,
                 can_reset: bool = True,
                 auto_add: bool = True,
                 ):
        super().__init__(action_base, var_name, default_value, can_reset, auto_add, on_change)

        self._widget: Scale = Scale(
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

        self.connect_signals()

    def connect_signals(self):
        self.widget.scale.connect("value-changed", self._value_changed)

    def disconnect_signals(self):
        better_disconnect(self.widget.scale, self._value_changed)

    def set_number(self, number: float, update_setting: bool = False):
        self.set_ui_value(number)

        if update_setting:
            self.set_value(number)

    def get_number(self) -> float:
        return self.widget.scale.get_value()

    def _value_changed(self, scale):
        self._handle_value_changed(scale.get_value())

    @GenerativeUI.signal_manager
    def set_ui_value(self, value: float):
        self.widget.scale.set_value(value)

    def set_min(self, min: float):
        self.widget.set_min(min)

    def set_max(self, max: float):
        self.widget.set_max(max)

    def set_step(self, step: float):
        self.widget.set_step(step)

    @property
    def min(self):
        return self.widget.min

    @min.setter
    def min(self, value: float):
        self.widget.min = value

    @property
    def max(self):
        return self.widget.max

    @max.setter
    def max(self, value: float):
        self.widget.max = value

    @property
    def step(self):
        return self.widget.step

    @step.setter
    def step(self, value: float):
        self.widget.step = value

    @property
    def digits(self):
        return self._widget.digits

    @digits.setter
    def digits(self, digits: int):
        self._widget.digits = digits