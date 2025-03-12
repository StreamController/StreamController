from abc import ABC, abstractmethod
from typing import TypeVar, Callable

import gi
from gi.repository import Gtk

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from src.backend.PluginManager import ActionCore

T = TypeVar("T")

class GenerativeUI[T](ABC):
    _action_core: "ActionCore"
    _var_name: str # name of the key in the actions settings
    _default_value: T # default value of the key
    on_change: Callable[[T], None] # method that gets called when the value changes
    widget: Gtk.Widget # The actual widget of the UI Element

    def __init__(self, action_core: "ActionCore", var_name: str, default_value: T, on_change: Callable[[T], None] = None):
        self._action_core = action_core
        self._var_name = var_name
        self._default_value = default_value
        self.on_change = on_change
        self.widget: Gtk.Widget = None

    @abstractmethod
    def get_ui(self) -> Gtk.Widget:
        pass

    @abstractmethod
    def set_ui_value(self, value: T):
        pass
    
    def _handle_value_changed(self, new_value: T):
        self.set_value(new_value)
        
        if self.on_change:
            self.on_change(new_value)

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
        settings = self._action_core.get_settings()

        settings[self._var_name] = value
        self._action_core.set_settings(settings)

    def get_value(self, fallback: T = None) -> T:
        """
        Returns the value from the settings
        """
        settings = self._action_core.get_settings()

        if fallback is None:
            fallback = self._default_value

        return settings.get(self._var_name, fallback)

    def load_initial_ui_value(self):
        value = self.get_value()
        self.set_ui_value(value)

    def get_translation(self, key: str, fallback: str):
        if key is None or fallback is None:
            return ""

        return self._action_base.get_translation(key, fallback)