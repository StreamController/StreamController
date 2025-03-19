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
    _action_base: "ActionBase"
    _var_name: str # name of the key in the actions settings
    _default_value: T # default value of the key
    on_change: Callable[[Gtk.Widget, T, T], None] # method that gets called when the value changes    _widget: Gtk.Widget # The actual widget of the UI Element
    _can_reset: bool
    _auto_add: bool

    def __init__(self, action_base: "ActionBase", var_name: str, default_value: T, can_reset: bool = True, auto_add: bool = True, on_change: Callable[[Gtk.Widget, T, T], None] = None):
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
        pass

    @abstractmethod
    def disconnect_signals(self):
        pass

    @property
    def action_base(self):
        return self._action_base

    @property
    def var_name(self):
        return self._var_name

    @property
    def default_value(self):
        return self._default_value

    @property
    def widget(self):
        return self._widget

    @property
    def can_reset(self):
        return self._can_reset

    @property
    def auto_add(self):
        return self._auto_add

    @staticmethod
    def signal_manager(func):
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
        pass
    
    def _handle_value_changed(self, new_value: T):
        old_value = self.get_value()

        self.set_value(new_value)
        
        if self.on_change:
            self.on_change(self.widget, new_value, old_value)

    def update_value_in_ui(self):
        value = self.get_value()
        self.set_ui_value(value)

    def reset_value(self):
        self.set_value(self._default_value)
        self.update_value_in_ui()

    def set_value(self, value: T):
        """
        Sets the settings with the given value
        """
        settings = self._action_base.get_settings()

        settings[self._var_name] = value
        self._action_base.set_settings(settings)

    def get_value(self, fallback: T = None) -> T:
        """
        Returns the value from the settings
        """
        settings = self._action_base.get_settings()

        if fallback is None:
            fallback = self._default_value

        return settings.get(self._var_name, fallback)

    def load_initial_ui_value(self):
        value = self.get_value()
        self.set_ui_value(value)

    def get_translation(self, key: str, fallback: str = None):
        if key is None:
            return ""

        return self._action_base.get_translation(key, fallback)

    def _create_reset_button(self):
        button = Gtk.Button(icon_name="edit-undo-symbolic", vexpand=True, css_classes=["no-rounded-corners"], overflow=Gtk.Overflow.HIDDEN)

        button.connect("clicked", lambda _: self.reset_value())

        return button
    
    def _get_suffix_box(self):
        return self.widget.get_first_child().get_last_child()
    
    def _handle_reset_button_creation(self):
        self.widget.add_css_class("gen-ui-row")
        self.widget.set_overflow(Gtk.Overflow.HIDDEN)
        self.widget.get_child().add_css_class("gen-ui-box")
        self.widget.get_child().set_overflow(Gtk.Overflow.HIDDEN)

        suffix_box = self._get_suffix_box()
        if suffix_box:
            suffix_box.add_css_class("no-margin")

        if self._can_reset:
            self.widget.add_suffix(self._create_reset_button())