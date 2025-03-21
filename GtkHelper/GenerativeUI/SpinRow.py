from GtkHelper.GenerativeUI.GenerativeUI import GenerativeUI

import gi
from gi.repository import Gtk, Adw

from typing import TYPE_CHECKING

from GtkHelper.GtkHelper import better_disconnect

if TYPE_CHECKING:
    from src.backend.PluginManager import ActionBase

class SpinRow(GenerativeUI[float]):
    """
    A class that represents a spin row widget, allowing the user to increment or decrement a numeric value
    using spin buttons. The widget can be customized with properties such as minimum, maximum, step size, and
    the number of digits displayed.

    Inherits from `GenerativeUI` to manage the UI and provide common functionality for interactive elements.

    Attributes:
        value (float): The current value of the spin row.
        min (float): The minimum allowed value for the spin row.
        max (float): The maximum allowed value for the spin row.
        step (float): The step size for incrementing/decrementing the value.
        digits (int): The number of digits to display for the value.
    """

    def __init__(self, action_base: "ActionBase",
                 var_name: str,
                 default_value: float,
                 min: float,
                 max: float,
                 title: str = None,
                 subtitle: str = None,
                 step: float = 0.1,
                 digits: int = 2,
                 on_change: callable = None,
                 can_reset: bool = True,
                 auto_add: bool = True,
                 complex_var_name: bool = False
                 ):
        """
        Initializes the SpinRow widget, setting up the spin buttons with the specified properties.

        Args:
            action_base (ActionBase): The base action associated with the spin row.
            var_name (str): The variable name associated with this spin row.
            default_value (float): The default value for the spin row.
            min (float): The minimum value for the spin row.
            max (float): The maximum value for the spin row.
            title (str, optional): The title to display for the spin row.
            subtitle (str, optional): The subtitle to display below the spin row.
            step (float, optional): The step size for the spin row. Defaults to 0.1.
            digits (int, optional): The number of digits to display for the spin value. Defaults to 2.
            on_change (callable, optional): A callback function to call when the spin value changes.
            can_reset (bool, optional): Whether the spin value can be reset. Defaults to True.
            auto_add (bool, optional): Whether to automatically add the spin row to the UI. Defaults to True.
        """
        super().__init__(action_base, var_name, default_value, can_reset, auto_add, complex_var_name, on_change)

        self._adjustment = Gtk.Adjustment.new(self._default_value, min, max, step, 1, 0)

        self._widget: Adw.SpinRow = Adw.SpinRow(
            title=self.get_translation(title, title),
            subtitle=self.get_translation(subtitle, subtitle),
            value=self._default_value,
            adjustment=self._adjustment,
        )
        self.widget.set_digits(digits)

        self._handle_reset_button_creation()

        self.connect_signals()

    def connect_signals(self):
        """
        Connects the signal handlers for the spin row widget to track changes in its value.
        """
        self._adjustment.connect("value-changed", self._correct_step_amount)
        self.widget.connect("changed", self._value_changed)

    def disconnect_signals(self):
        """
        Disconnects the signal handlers for the spin row widget.
        """
        better_disconnect(self._adjustment, self._correct_step_amount)
        better_disconnect(self.widget, self._value_changed)

    def set_number(self, number: float, update_setting: bool = False):
        """
        Sets the value of the spin row widget and optionally updates the associated setting.

        Args:
            number (float): The new value for the spin row.
            update_setting (bool, optional): If True, updates the setting with the new value. Defaults to False.
        """
        self.set_ui_value(number)

        if update_setting:
            self.set_value(number)

    def get_number(self) -> float:
        """
        Retrieves the current value of the spin row.

        Returns:
            float: The current value of the spin row.
        """
        return self.widget.get_value()

    def _value_changed(self, spin: Adw.SpinRow):
        """
        Handles the change in spin row value.

        This method is called when the user adjusts the spin row value. It updates the associated value accordingly.

        Args:
            spin (Adw.SpinRow): The spin row widget whose value changed.
        """
        self._handle_value_changed(spin.get_value())

    @GenerativeUI.signal_manager
    def set_ui_value(self, value: float):
        """
        Sets the value of the spin row widget in the UI.

        Args:
            value (float): The value to set in the spin row widget.
        """
        self.widget.set_value(value)

    def _correct_step_amount(self, adjustment):
        """
        Corrects the step amount to ensure it is in multiples of the step size.

        This method is called when the value of the adjustment changes to round the value to the nearest
        multiple of the step increment.

        Args:
            adjustment (Gtk.Adjustment): The adjustment widget whose value changed.
        """
        value = adjustment.get_value()
        step = adjustment.get_step_increment()
        rounded_value = round(value / step) * step
        adjustment.set_value(rounded_value)

    @property
    def min(self):
        return self._adjustment.get_lower()

    @min.setter
    def min(self, value: float):
        """
        Sets the minimum value for the spin row.

        Args:
            value (float): The minimum value for the spin row.
        """
        if self._adjustment.get_upper() < value:
            return

        self._adjustment.set_lower(value)

    @property
    def max(self):
        return self._adjustment.get_upper()

    @max.setter
    def max(self, value: float):
        """
        Sets the maximum value for the spin row.
        Args:
            max (float): The maximum value for the spin row.
        """
        if value < self._adjustment.get_lower():
            return

        self._adjustment.set_upper(value)

    @property
    def step(self):
        return self._adjustment.get_step_increment()

    @step.setter
    def step(self, value: float):
        """
        Sets the step size for adjusting the spin row value.
        Args:
            value (float): The step size for the spin row.
        """
        self._adjustment.set_step_increment(value)