import functools
from abc import ABC, abstractmethod
from typing import TypeVar, Callable

import gi
from gi.repository import Gtk

from typing import TYPE_CHECKING

from globals import signal_manager

if TYPE_CHECKING:
    from src.backend.PluginManager import ActionBase

T = TypeVar("T")

class GenerativeUI[T](ABC):
    """
       Abstract base class for creating dynamic UI elements linked to an `ActionBase` instance.

       Attributes:
           _action_base (ActionBase): The action this UI element is associated with.
           _var_name (str): The key used to store the value in the action's settings.
           _default_value (T): The default value for this UI element.
           on_change (Callable[[Gtk.Widget, T, T], None]): Function called when the value changes.
           _widget (Gtk.Widget): The GTK widget representing the UI element.
           _can_reset (bool): Whether the UI element can be reset to its default value.
           _auto_add (bool): Whether the UI element is automatically added to the action.
       """
    _action_base: "ActionBase"
    _var_name: str # name of the key in the actions settings
    _default_value: T # default value of the key
    on_change: Callable[[Gtk.Widget, T, T], None] # method that gets called when the value changes    _widget: Gtk.Widget # The actual widget of the UI Element
    _can_reset: bool
    _auto_add: bool

    def __init__(self, action_base: "ActionBase", var_name: str, default_value: T, can_reset: bool = True,
                 auto_add: bool = True, on_change: Callable[[Gtk.Widget, T, T], None] = None):
        """
        Initializes the UI element.

        Args:
            action_base (ActionBase): The action this UI element is associated with.
            var_name (str): The key used to store the value in the action's settings.
            default_value (T): The default value for this UI element.
            can_reset (bool, optional): Whether the UI element can be reset. Defaults to True.
            auto_add (bool, optional): Whether the UI element is automatically added to the action. Defaults to True.
            on_change (Callable[[Gtk.Widget, T, T], None], optional): Function called when the value changes. Defaults to None.
        """
        self._action_base = action_base
        self._var_name = var_name
        self._default_value = default_value
        self.on_change = on_change
        self._can_reset = can_reset
        self._auto_add = auto_add
        self._widget: Gtk.Widget = None

        self._action_base.add_generative_ui_object(self)

    @abstractmethod
    def connect_signals(self):
        """Connects signals for the UI element."""
        pass

    @abstractmethod
    def disconnect_signals(self):
        """Disconnects signals for the UI element."""
        pass

    @property
    def action_base(self):
        """Returns the associated `ActionBase` instance."""
        return self._action_base

    @property
    def var_name(self):
        """Returns the variable name used in settings."""
        return self._var_name

    @property
    def default_value(self):
        """Returns the default value of the UI element."""
        return self._default_value

    @property
    def widget(self):
        """Returns the GTK widget representing the UI element."""
        return self._widget

    @property
    def can_reset(self):
        """Returns whether the UI element can be reset."""
        return self._can_reset

    @property
    def auto_add(self):
        """Returns whether the UI element is automatically added to the action."""
        return self._auto_add

    @staticmethod
    def signal_manager(func):
        """
        Decorator to manage signal connections by disconnecting and reconnecting signals around the function call.

        Args:
            func (Callable): The function to wrap.

        Returns:
            Callable: The wrapped function.
        """

        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            self.disconnect_signals()
            try:
                return func(self, *args, **kwargs)
            finally:
                self.connect_signals()

        return wrapper

    @abstractmethod
    @signal_manager
    def set_ui_value(self, value: T):
        """
        Sets the UI element to the specified value.

        Args:
            value (T): The value to set in the UI.
        """
        pass

    def _handle_value_changed(self, new_value: T):
        """
        Handles changes in the UI element's value.

        Args:
            new_value (T): The new value of the UI element.
        """
        old_value = self.get_value()
        self.set_value(new_value)

        if self.on_change:
            self.on_change(self.widget, new_value, old_value)

    def update_value_in_ui(self):
        """Updates the UI element with the current value from settings."""
        value = self.get_value()
        self.set_ui_value(value)

    def reset_value(self):
        """Resets the UI element to its default value."""
        self._handle_value_changed(self._default_value)
        self.update_value_in_ui()

    def set_value(self, value: T):
        """
        Sets the value in the action's settings.

        Args:
            value (T): The value to set.
        """
        settings = self._action_base.get_settings()
        settings[self._var_name] = value
        self._action_base.set_settings(settings)

    def get_value(self, fallback: T = None) -> T:
        """
        Retrieves the value from the action's settings.

        Args:
            fallback (T, optional): The fallback value if the key is not found. Defaults to None.

        Returns:
            T: The retrieved value.
        """
        settings = self._action_base.get_settings()
        return settings.get(self._var_name, fallback or self._default_value)

    def load_initial_ui(self):
        """Loads the initial UI state based on the stored value."""
        value = self.get_value()
        self._handle_value_changed(value)

    def load_ui_value(self):
        """Loads the UI element with the stored value."""
        value = self.get_value()
        self.set_ui_value(value)

    def get_translation(self, key: str, fallback: str = None):
        """
        Retrieves a translated string for the given key.

        Args:
            key (str): The translation key.
            fallback (str, optional): The fallback text if translation is not found.

        Returns:
            str: The translated string.
        """
        return self._action_base.get_translation(key, fallback) if key else ""

    def unparent(self):
        """Removes the UI element from its parent widget if it has one."""
        if self.widget and self.widget.get_parent():
            self.widget.unparent()

    def _create_reset_button(self):
        """Creates a reset button for the UI element."""
        button = Gtk.Button(icon_name="edit-undo-symbolic", vexpand=True, css_classes=["no-rounded-corners"],
                            overflow=Gtk.Overflow.HIDDEN)
        button.connect("clicked", lambda _: self.reset_value())
        return button

    def _get_suffix_box(self):
        """
        Retrieves the suffix box widget from the UI element.

        Returns:
            Gtk.Widget: The suffix box widget.
        """
        return self.widget.get_first_child().get_last_child()

    def _handle_reset_button_creation(self):
        """
        Handles the creation and addition of the reset button to the UI element.
        """

        if not self.can_reset:
            return

        self.widget.add_css_class("gen-ui-row")
        self.widget.set_overflow(Gtk.Overflow.HIDDEN)
        self.widget.get_child().add_css_class("gen-ui-box")
        self.widget.get_child().set_overflow(Gtk.Overflow.HIDDEN)

        suffix_box = self._get_suffix_box()
        if suffix_box:
            suffix_box.add_css_class("no-margin")

        if self._can_reset:
            self.widget.add_suffix(self._create_reset_button())