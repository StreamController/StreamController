from GtkHelper.GenerativeUI.GenerativeUI import GenerativeUI

import gi
from gi.repository import Gtk, Adw, GLib

from typing import TYPE_CHECKING, Callable
from GtkHelper.GtkHelper import better_disconnect

if TYPE_CHECKING:
    from src.backend.PluginManager import ActionCore

class EntryRow(GenerativeUI[str]):
    """
    A class that represents a UI entry row widget with additional functionality
    for handling text input and providing filters or transformations on the input.

    Inherits from `GenerativeUI` to provide generic UI management and functionality.

    Attributes:
        filter_func (Callable[[str], str]): Optional function to filter or transform the input text.
    """

    def __init__(self, action_core: "ActionCore",
                 var_name: str,
                 default_value: str,
                 title: str = None,
                 filter_func: Callable[[str], str] = None,
                 on_change: callable = None,
                 can_reset: bool = True,
                 auto_add: bool = True,
                 complex_var_name: bool = False
                 ):
        """
        Initializes the EntryRow widget.

        Args:
            action_core (ActionCore): The base action that provides context for this entry row.
            var_name (str): The variable name to associate with this entry row.
            default_value (str): The default text to display in the entry row.
            title (str, optional): The title to display for the entry row.
            filter_func (Callable[[str], str], optional): A function to filter or transform the text input.
            on_change (callable, optional): A callback function to call when the value changes.
            can_reset (bool, optional): Whether the value can be reset. Defaults to True.
            auto_add (bool, optional): Whether to automatically add this entry to the UI. Defaults to True.
        """
        super().__init__(action_core, var_name, default_value, can_reset, auto_add, complex_var_name, on_change)

        self._widget: Adw.EntryRow = Adw.EntryRow(
            title=self.get_translation(title, title),
            text=self._default_value
        )

        self.filter_func = filter_func
        self._handle_reset_button_creation()
        self.connect_signals()

    def connect_signals(self):
        """
        Connects the signal handlers for the widget, specifically the 'changed' signal
        to trigger the value change handling method.

        This ensures that when the text in the entry row changes, the value is handled accordingly.
        """
        self.widget.connect("changed", self._value_changed)

    def disconnect_signals(self):
        """
        Disconnects the signal handlers to prevent further handling of the 'changed' signal.

        This method ensures that the signal is disconnected when the widget is no longer in use or needs to stop handling changes.
        """
        better_disconnect(self.widget, self._value_changed)

    def set_text(self, text: str, update_setting: bool = False):
        """
        Sets the text in the entry row widget and optionally updates the associated setting.

        Args:
            text (str): The text to set in the widget.
            update_setting (bool, optional): If True, updates the setting with the new text. Defaults to False.
        """
        self.set_ui_value(text)

        if update_setting:
            self.set_value(text)

    def get_text(self) -> str:
        """
        Retrieves the current text from the entry row widget.

        Returns:
            str: The current text in the entry row.
        """
        return self.widget.get_text()

    def _text_reset(self, text):
        """
        Resets the text in the entry row to the provided value and adjusts the cursor position.

        This method handles disconnecting and reconnecting signals while ensuring the cursor position
        is managed correctly when resetting the value.

        Args:
            text (str): The text to reset in the entry row.
        """
        better_disconnect(self.widget, self._value_changed)

        cursor_pos = self.widget.get_position()
        text_is_filtered = text != self.widget.get_text()

        self.set_ui_value(text)

        if text_is_filtered:
            self.widget.set_position(cursor_pos - 1)
        else:
            self.widget.set_position(cursor_pos)

        self.widget.connect("changed", self._value_changed)

    def _value_changed(self, entry_row: Adw.EntryRow):
        """
        Handles the value change in the entry row widget.

        This method is called whenever the text in the entry row changes. It applies the filter function, if provided,
        and resets the text accordingly.

        Args:
            entry_row (Adw.EntryRow): The entry row widget whose value has changed.
        """
        text = entry_row.get_text()

        if self.filter_func is not None:
            text = self.filter_func(text)

        GLib.idle_add(self._text_reset, text)
        self._handle_value_changed(text)

    @GenerativeUI.signal_manager
    def set_ui_value(self, value: str):
        """
        Sets the value in the UI widget.

        This method updates the UI widget with the provided value.

        Args:
            value (str): The value to set in the UI widget.
        """
        self.widget.set_text(value)