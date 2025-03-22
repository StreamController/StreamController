from GtkHelper.GenerativeUI.GenerativeUI import GenerativeUI

import gi
from gi.repository import Gtk, Adw

from typing import TYPE_CHECKING

from GtkHelper.GtkHelper import better_disconnect

if TYPE_CHECKING:
    from src.backend.PluginManager.ActionCore import ActionCore

class SwitchRow(GenerativeUI[bool]):
    """
    A class that represents a switch row widget, allowing the user to toggle between two states: on (True) or off (False).

    Inherits from `GenerativeUI` to manage the UI and provide common functionality for interactive elements.

    Attributes:
        active (bool): The current state of the switch (True for on, False for off).
    """

    def __init__(self, action_core: "ActionCore",
                 var_name: str,
                 default_value: bool,
                 title: str = None,
                 subtitle: str = None,
                 on_change: callable = None,
                 can_reset: bool = True,
                 auto_add: bool = True,
                 complex_var_name: bool = False
                 ):
        """
        Initializes the SwitchRow widget, setting up the switch with the specified properties.

        Args:
            action_core (ActionCore): The base action associated with the switch row.
            var_name (str): The variable name associated with this switch row.
            default_value (bool): The default value for the switch row (True for on, False for off).
            title (str, optional): The title to display for the switch row.
            subtitle (str, optional): The subtitle to display below the switch row.
            on_change (callable, optional): A callback function to call when the switch state changes.
            can_reset (bool, optional): Whether the switch value can be reset. Defaults to True.
            auto_add (bool, optional): Whether to automatically add the switch row to the UI. Defaults to True.
        """
        super().__init__(action_core, var_name, default_value, can_reset, auto_add, complex_var_name, on_change)

        self._widget: Adw.SwitchRow = Adw.SwitchRow(
            title=self.get_translation(title, title),
            subtitle=self.get_translation(subtitle, subtitle),
            active=default_value
        )

        self._handle_reset_button_creation()
        self.connect_signals()

    def connect_signals(self):
        """
        Connects the signal handler for the switch widget to track changes in its state.
        """
        self.widget.connect("notify::active", self._value_changed)

    def disconnect_signals(self):
        """
        Disconnects the signal handler for the switch widget.
        """
        better_disconnect(self.widget, self._value_changed)

    def set_active(self, active: bool, change_setting: bool = False):
        """
        Sets the state of the switch widget and optionally updates the associated setting.

        Args:
            active (bool): The new state of the switch (True for on, False for off).
            change_setting (bool, optional): If True, updates the setting with the new state. Defaults to False.
        """
        self.set_ui_value(active)

        if change_setting:
            self.set_value(active)

    def get_active(self) -> bool:
        """
        Retrieves the current state of the switch.

        Returns:
            bool: The current state of the switch (True for on, False for off).
        """
        return self.widget.get_active()

    def _value_changed(self, switch, _):
        """
        Handles the change in switch state.

        This method is called when the user toggles the switch. It updates the associated value accordingly.

        Args:
            switch (Adw.SwitchRow): The switch widget whose state changed.
            _ (str): Placeholder for unused argument.
        """
        self._handle_value_changed(switch.get_active())

    @GenerativeUI.signal_manager
    def set_ui_value(self, value: bool):
        """
        Sets the state of the switch widget in the UI.

        Args:
            value (bool): The state to set for the switch (True for on, False for off).
        """
        self.widget.set_active(value)