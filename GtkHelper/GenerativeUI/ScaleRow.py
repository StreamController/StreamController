from GtkHelper.GenerativeUI.GenerativeUI import GenerativeUI

import gi
from gi.repository import Gtk, Adw

from typing import TYPE_CHECKING

from GtkHelper.GtkHelper import better_disconnect

if TYPE_CHECKING:
    from src.backend.PluginManager import ActionCore

from GtkHelper.ScaleRow import ScaleRow as Scale

class ScaleRow(GenerativeUI[float]):
    """
    A class that represents a scale row widget, which allows the user to select a numeric value from a range
    using a slider. The widget can be configured with various properties such as min, max, step, and the display of
    a text entry field for manual value input.

    Inherits from `GenerativeUI` to provide generic UI management and functionality.

    Attributes:
        value (float): The current value of the scale.
        min (float): The minimum allowed value for the scale.
        max (float): The maximum allowed value for the scale.
        step (float): The step size for adjusting the scale value.
        digits (int): The number of digits to display for the scale value.
    """

    def __init__(self, action_core: "ActionCore",
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
                 complex_var_name: bool = False
                 ):
        """
        Initializes the ScaleRow widget, setting up the scale UI component with the specified properties.

        Args:
            action_core (ActionCore): The base action associated with the scale row.
            var_name (str): The variable name associated with this scale row.
            default_value (float): The default value for the scale.
            min (float): The minimum value for the scale.
            max (float): The maximum value for the scale.
            title (str, optional): The title to display for the scale row.
            subtitle (str, optional): The subtitle to display below the scale row.
            step (float, optional): The step size for the scale. Defaults to 0.1.
            digits (int, optional): The number of digits to display for the scale value. Defaults to 2.
            draw_value (bool, optional): Whether to display the current value next to the scale. Defaults to True.
            round_digits (bool, optional): Whether to round the value to the specified number of digits. Defaults to True.
            add_text_entry (bool, optional): Whether to add a text entry field for manual input of the scale value. Defaults to False.
            text_entry_max_length (int, optional): The maximum length of the text entry if enabled. Defaults to 6.
            on_change (callable, optional): A callback function to call when the scale value changes.
            can_reset (bool, optional): Whether the scale value can be reset. Defaults to True.
            auto_add (bool, optional): Whether to automatically add the scale row to the UI. Defaults to True.
        """
        super().__init__(action_core, var_name, default_value, can_reset, auto_add, complex_var_name, on_change)

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
        """
        Connects the signal handler for the 'value-changed' signal to track changes in the scale's value.

        This ensures that when the scale value is changed, the appropriate callback is called to handle the change.
        """
        self.widget.scale.connect("value-changed", self._value_changed)

    def disconnect_signals(self):
        """
        Disconnects the signal handler for the 'value-changed' signal.

        This method prevents further handling of scale value changes when the widget is no longer in use or
        when the signals should be stopped.
        """
        better_disconnect(self.widget.scale, self._value_changed)

    def set_number(self, number: float, update_setting: bool = False):
        """
        Sets the scale value and optionally updates the associated setting.

        Args:
            number (float): The new value for the scale.
            update_setting (bool, optional): If True, updates the setting with the new scale value. Defaults to False.
        """
        self.set_ui_value(number)

        if update_setting:
            self.set_value(number)

    def get_number(self) -> float:
        """
        Retrieves the current value of the scale.

        Returns:
            float: The current value of the scale.
        """
        return self.widget.scale.get_value()

    def _value_changed(self, scale):
        """
        Handles the change in scale value.

        This method is triggered when the user adjusts the scale, updating the associated value.

        Args:
            scale (Gtk.Scale): The scale widget whose value changed.
        """
        self._handle_value_changed(scale.get_value())

    @GenerativeUI.signal_manager
    def set_ui_value(self, value: float):
        """
        Sets the value of the scale widget in the UI.

        Args:
            value (float): The value to set in the scale widget.
        """
        self.widget.scale.set_value(value)

    def set_min(self, min: float):
        """
        Sets the minimum value for the scale.

        Args:
            min (float): The minimum value for the scale.
        """
        self.widget.set_min(min)

    def set_max(self, max: float):
        """
        Sets the maximum value for the scale.

        Args:
            max (float): The maximum value for the scale.
        """
        self.widget.set_max(max)

    def set_step(self, step: float):
        """
        Sets the step size for adjusting the scale value.

        Args:
            step (float): The step size for the scale.
        """
        self.widget.set_step(step)

    @property
    def min(self):
        """
        Gets the minimum value for the scale.

        Returns:
            float: The minimum value for the scale.
        """
        return self.widget.min

    @min.setter
    def min(self, value: float):
        """
        Sets the minimum value for the scale.

        Args:
            value (float): The new minimum value for the scale.
        """
        self.widget.min = value

    @property
    def max(self):
        """
        Gets the maximum value for the scale.

        Returns:
            float: The maximum value for the scale.
        """
        return self.widget.max

    @max.setter
    def max(self, value: float):
        """
        Sets the maximum value for the scale.

        Args:
            value (float): The new maximum value for the scale.
        """
        self.widget.max = value

    @property
    def step(self):
        """
        Gets the step size for adjusting the scale value.

        Returns:
            float: The step size for the scale.
        """
        return self.widget.step

    @step.setter
    def step(self, value: float):
        """
        Sets the step size for adjusting the scale value.

        Args:
            value (float): The new step size for the scale.
        """
        self.widget.step = value

    @property
    def digits(self):
        """
        Gets the number of digits to display for the scale value.

        Returns:
            int: The number of digits for the scale value.
        """
        return self._widget.digits

    @digits.setter
    def digits(self, digits: int):
        """
        Sets the number of digits to display for the scale value.

        Args:
            digits (int): The number of digits for the scale value.
        """
        self._widget.digits = digits