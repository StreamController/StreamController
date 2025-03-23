from functools import partial

from GtkHelper.GenerativeUI.GenerativeUI import GenerativeUI

import gi
from gi.repository import Gtk, Adw, GLib

from typing import TYPE_CHECKING, Callable
from GtkHelper.GtkHelper import better_disconnect

if TYPE_CHECKING:
    from src.backend.PluginManager.ActionCore import ActionCore

from GtkHelper.GtkHelper import BetterExpander

class ExpanderRow(GenerativeUI[bool]):
    """
    A class that represents a UI expander row widget with additional functionality
    to manage its expansion state and to add child widgets.

    Inherits from `GenerativeUI` to provide generic UI management and functionality.

    Attributes:
        expanded (bool): Whether the expander is currently expanded or collapsed.
    """

    def __init__(self, action_core: "ActionCore",
                 var_name: str,
                 default_value: bool,
                 title: str = None,
                 subtitle: str = None,
                 show_enable_switch: bool = False,
                 start_expanded: bool = False,
                 on_change: callable = None,
                 can_reset: bool = False,
                 auto_add: bool = True,
                 complex_var_name: bool = False
                 ):
        """
        Initializes the ExpanderRow widget.

        Args:
            action_core (ActionCore): The base action that provides context for this expander row.
            var_name (str): The variable name to associate with this expander row.
            default_value (bool): The default expanded/collapsed state of the expander.
            title (str, optional): The title to display for the expander row.
            subtitle (str, optional): The subtitle to display for the expander row.
            show_enable_switch (bool, optional): Whether to show the enable switch. Defaults to False.
            start_expanded (bool, optional): Whether the expander should start in an expanded state. Defaults to False.
            on_change (callable, optional): A callback function to call when the value changes.
            can_reset (bool, optional): Whether the value can be reset. Defaults to False.
            auto_add (bool, optional): Whether to automatically add this entry to the UI. Defaults to True.
        """
        super().__init__(action_core, var_name, default_value, can_reset, auto_add, complex_var_name, on_change)

        self._widget: BetterExpander = BetterExpander(
            title=self.get_translation(title),
            subtitle=self.get_translation(subtitle),
            expanded=start_expanded,
            show_enable_switch=show_enable_switch
        )

        self._switch_enabled = show_enable_switch

        self._handle_reset_button_creation()
        self.connect_signals()

    def connect_signals(self):
        """
        Connects the signal handler for the 'notify::enable-expansion' signal to track changes
        in the expansion state of the expander widget.

        This ensures that when the expander's enabled state changes, the value is handled accordingly.
        """
        self.widget.connect("notify::enable-expansion", self._value_changed)

    def disconnect_signals(self):
        """
        Disconnects the signal handler for the 'notify::enable-expansion' signal.

        This method prevents further handling of expansion state changes when the widget is no longer in use
        or when the signals should be stopped.
        """
        better_disconnect(self.widget, self._value_changed)

    def set_enable_expansion(self, enable_expansion: bool, update_setting: bool = False):
        """
        Sets the expansion state for the expander and optionally updates the associated setting.

        Args:
            enable_expansion (bool): Whether to enable expansion for the expander.
            update_setting (bool, optional): If True, updates the setting with the new state. Defaults to False.
        """
        self.set_ui_value(enable_expansion)

        if update_setting:
            self.set_value(enable_expansion)

    def get_enable_expansion(self) -> bool:
        """
        Retrieves the current expansion state of the expander.

        Returns:
            bool: The current state of the expander's enabled expansion.
        """
        return self.widget.get_enable_expansion()

    def add_row(self, widget: Gtk.Widget):
        """
        Adds a widget as a row to the expander. If the widget already has a parent,
        it is removed before being added to the expander.

        Args:
            widget (Gtk.Widget): The widget to add as a row in the expander.
        """
        if widget.get_parent() is not None:
            self.widget.remove_child(widget)
            widget.unparent()
        self.widget.add_row(widget)

    def clear_rows(self):
        self.widget.clear()

    def _value_changed(self, expander_row: BetterExpander, _):
        """
        Handles the change in the expander's expansion state.

        This method is triggered when the expansion state of the expander widget changes,
        and it handles updating the associated value accordingly.

        Args:
            expander_row (BetterExpander): The expander row widget whose expansion state changed.
            _: Placeholder for additional unused parameters.
        """
        self._handle_value_changed(expander_row.get_enable_expansion())

    def _handle_value_changed(self, new_value: bool, update_setting: bool = True, trigger_callback: bool = True):
        if not self._switch_enabled:
            return
        super()._handle_value_changed(new_value, update_setting, trigger_callback)

    @GenerativeUI.signal_manager
    def set_ui_value(self, value: bool):
        """
        Sets the expansion state of the expander in the UI widget.

        Args:
            value (bool): The expansion state to set for the UI widget (expanded or collapsed).
        """
        if not self._switch_enabled:
            return

        self.widget.set_enable_expansion(value)

    def set_expanded(self, value: bool):
        self.widget.set_expanded(value)

    def get_expanded(self):
        return self.widget.get_expanded()