from dataclasses import dataclass

from GtkHelper.GenerativeUI.GenerativeUI import GenerativeUI
from GtkHelper.ColorButtonRow import ColorButtonRow as ColorDialog

import gi
from gi.repository import Gtk, Adw, Gio

from typing import TYPE_CHECKING, Callable

from GtkHelper.GtkHelper import better_disconnect

if TYPE_CHECKING:
    from src.backend.PluginManager import ActionBase


class ColorButtonRow(GenerativeUI[tuple[int, int, int, int]]):
    """
    A UI component for selecting and managing colors, extending GenerativeUI.

    Attributes:
        _widget (ColorDialog): The color selection dialog.
    """

    def __init__(self,
                 action_base: "ActionBase",
                 var_name: str,
                 default_value: tuple[int, int, int, int],
                 title: str = None,
                 subtitle: str = None,
                 on_change: Callable[[Gtk.Widget, tuple[int, int, int, int], tuple[int, int, int, int]], None] = None,
                 can_reset: bool = True,
                 auto_add: bool = True,
                 ):
        """
        Initializes the ColorButtonRow UI component.

        Args:
            action_base (ActionBase): The action this UI element is associated with.
            var_name (str): The key used to store the value in the action's settings.
            default_value (tuple[int, int, int, int]): The default RGBA color.
            title (str, optional): The title for the UI element.
            subtitle (str, optional): The subtitle for the UI element.
            on_change (Callable, optional): Function called when the color changes.
            can_reset (bool, optional): Whether the UI element can be reset. Defaults to True.
            auto_add (bool, optional): Whether the UI element is automatically added to the action. Defaults to True.
        """
        super().__init__(action_base, var_name, default_value, can_reset, auto_add, on_change)

        self._widget: ColorDialog = ColorDialog(
            title=self.get_translation(title),
            subtitle=self.get_translation(subtitle),
            default_color=self._default_value
        )

        self._handle_reset_button_creation()
        self.connect_signals()

    def connect_signals(self):
        """
        Connects the necessary signals for detecting color changes.
        """
        self.widget.color_button.connect("color-set", self._value_changed)

    def disconnect_signals(self):
        """
        Disconnects signals to prevent unwanted behavior.
        """
        better_disconnect(self.widget.color_button, self._value_changed)

    def set_color(self, color: tuple[int, int, int, int], update_setting: bool):
        """
        Sets the color in the UI and optionally updates the stored value.

        Args:
            color (tuple[int, int, int, int]): The new RGBA color.
            update_setting (bool): Whether to update the stored setting.
        """
        self.set_ui_value(color)

        if update_setting:
            self.set_value(color)

    def get_color(self) -> tuple[int, int, int, int]:
        """
        Retrieves the currently selected color.

        Returns:
            tuple[int, int, int, int]: The RGBA color tuple.
        """
        return self.widget.color

    def _value_changed(self, button: Gtk.ColorButton):
        """
        Handles the event when the color is changed in the UI.

        Args:
            button (Gtk.ColorButton): The color button that triggered the event.
        """
        self._handle_value_changed(self.widget.color)

    @GenerativeUI.signal_manager
    def set_ui_value(self, value: tuple[int, int, int, int]):
        """
        Updates the UI with the given color.

        Args:
            value (tuple[int, int, int, int]): The new RGBA color value.
        """
        self.widget.color = value

    def convert_from_rgba(self, color: "Gdk.RGBA") -> tuple[int, int, int, int]:
        return self.widget.convert_from_rgba(color)

    def convert_to_rgba(self, color: tuple[int, int, int, int]) -> "Gdk.RGBA":
        return self.widget.convert_to_rgba(color)

    def normalize_to_255(self, color: tuple[float, float, float, float]) -> tuple[int, int, int, int]:
        return self.widget.normalize_to_255(color)

    def normalize_to_1(self, color: tuple[int, int, int, int]) -> tuple[float, float, float, float]:
        return self.widget.normalize_to_1(color)