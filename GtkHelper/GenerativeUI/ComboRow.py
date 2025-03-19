from GtkHelper.ComboRow import ComboRow as Combo, BaseComboRowItem
from GtkHelper.GenerativeUI.GenerativeUI import GenerativeUI

import gi
from gi.repository import Gtk, Adw

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from src.backend.PluginManager import ActionBase

from GtkHelper.GtkHelper import better_disconnect

class ComboRow(GenerativeUI[BaseComboRowItem]):
    def __init__(self,
                 action_base: "ActionBase",
                 var_name: str,
                 default_value: BaseComboRowItem | str,
                 items: list[BaseComboRowItem] | list[str],
                 title: str = None,
                 subtitle: str = None,
                 enable_search: bool = False,
                 on_change: callable = None,
                 can_reset: bool = True,
                 auto_add: bool = True,
                 ):
        super().__init__(action_base, var_name, default_value, can_reset, auto_add, on_change)

        self._widget: Combo = Combo(
            title=self.get_translation(title, title),
            subtitle=self.get_translation(subtitle, subtitle),
            items=items,
            enable_search=enable_search,
            default_selection=self._default_value
        )

        self._handle_reset_button_creation()
        self.connect_signals()

    def connect_signals(self):
        self.widget.connect("notify::selected", self._value_changed)

    def disconnect_signals(self):
        better_disconnect(self.widget, self._value_changed)

    def _value_changed(self, combo_row: Combo, _):
        item = combo_row.get_selected_item()
        self._handle_value_changed(item)

    def _handle_value_changed(self, item: BaseComboRowItem):
        old_value = self.get_value(self._default_value)
        old_value = self.get_item(old_value)

        self.set_value(str(item))

        if self.on_change:
            self.on_change(self.widget, item, old_value)

    @GenerativeUI.signal_manager
    def set_ui_value(self, value: BaseComboRowItem | str):
        self.widget.set_selected_item(value)

    # Widget Wrappers

    def set_selected_item(self, item: BaseComboRowItem | str = "", update_setting: bool = False):
        self.set_ui_value(item)

        if update_setting:
            self.set_value(str(item))

    @GenerativeUI.signal_manager
    def add_item(self, combo_row_item: BaseComboRowItem | str):
        self.widget.add_item(combo_row_item)

    @GenerativeUI.signal_manager
    def add_items(self, items: list[BaseComboRowItem] | str):
        self.widget.add_items(items)

    @GenerativeUI.signal_manager
    def remove_item_at_index(self, index: int):
        self.widget.remove_item_at_index(index)

    @GenerativeUI.signal_manager
    def remove_item(self, item: BaseComboRowItem | str):
        self.widget.remove_item(item)

    @GenerativeUI.signal_manager
    def remove_items(self, start: int, amount: int):
        self.widget.remove_items(start, amount)

    @GenerativeUI.signal_manager
    def remove_all_items(self):
        self.widget.remove_all_items()

    def get_item_at(self, index: int) -> BaseComboRowItem:
        return self.widget.get_item_at(index)

    def get_item(self, name: str) -> BaseComboRowItem:
        return self.widget.get_item(name)

    def get_selected_item(self) -> BaseComboRowItem | None:
        return self.widget.get_selected_item()

    @GenerativeUI.signal_manager
    def populate(self, items: list[BaseComboRowItem], selected_item: BaseComboRowItem | str = "", update_setting: bool = False):
        self.remove_all_items()
        self.add_items(items)
        self.set_selected_item(selected_item)

        if update_setting:
            self.set_value(str(self.get_selected_item()))

        self.update_value_in_ui()