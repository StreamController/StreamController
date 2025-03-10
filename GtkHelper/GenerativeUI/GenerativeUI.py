from abc import ABC, abstractmethod
from typing import TypeVar, Generic

import gi
from gi.repository import Gtk

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from src.backend.PluginManager import ActionBase

T = TypeVar("T")

class GenerativeUI(ABC, Generic[T]):
    action_base: "ActionBase"
    var_name: str
    default_value: T
    on_change: callable
    widget: Gtk.Widget

    def __init__(self, action_base: "ActionBase", var_name: str, default_value: T, on_change: callable = None):
        self.action_base = action_base
        self.var_name = var_name
        self.default_value = default_value
        self.on_change = on_change
        self.widget: Gtk.Widget = None

    @abstractmethod
    def get_ui(self) -> Gtk.Widget:
        pass

    @abstractmethod
    def set_ui_value(self, value: T):
        pass

    def get_value(self) -> T:
        return self.get_key(self.var_name, self.default_value)
    
    def _handle_value_changed(self, new_value: T):
        self.set_key(self.var_name, new_value)
        
        if self.on_change:
            self.on_change(new_value)

    def load_value(self):
        self.set_ui_value(self.get_key(self.var_name))

    def set_key(self, key: str, value: T):
        settings = self.action_base.get_settings()
        settings[key] = value
        self.action_base.set_settings(settings)

    def get_key(self, key: str, fallback: T) -> T:
        settings = self.action_base.get_settings()
        return settings.get(key, fallback)

    def load_initial_ui_value(self):
        self.set_ui_value(self.get_value())