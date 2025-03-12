from GtkHelper.GenerativeUI.GenerativeUI import GenerativeUI

import gi
from gi.repository import Gtk, Adw

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from src.backend.PluginManager import ActionBase

class SpinRow(GenerativeUI[float]):
    def __init__(self, action_base: "ActionBase",
                 var_name: str,
                 default_value: float,
                 min: float,
                 max: float,
                 on_change: callable = None,
                 title: str = None,
                 subtitle: str = None,
                 step: float = 0.1,
                 digits: int = 2,
                 ):
        super().__init__(action_base, var_name, default_value, on_change)

        adjustment = Gtk.Adjustment.new(self._default_value, min, max, step, 1, 0)

        self.widget: Adw.SpinRow = Adw.SpinRow(
            title=self.get_translation(title, title),
            subtitle=self.get_translation(subtitle, subtitle),
            value=self._default_value,
            adjustment=adjustment,
        )
        self.widget.set_digits(digits)

        adjustment.connect("value-changed", self._correct_step_amount)

    def _value_changed(self, spin: Adw.SpinRow, _):
        self._handle_value_changed(spin.get_value())
    
    def set_ui_value(self, value: float):
        self.widget.set_value(value)

    def _correct_step_amount(self, adjustment):
        value = adjustment.get_value()
        step = adjustment.get_step_increment()
        rounded_value = round(value / step) * step
        adjustment.set_value(rounded_value)