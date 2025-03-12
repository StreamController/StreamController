from GtkHelper.ComboRow import ComboRow as Combo, BaseComboRowItem
from GtkHelper.GenerativeUI.GenerativeUI import GenerativeUI

import gi
from gi.repository import Gtk, Adw

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from src.backend.PluginManager import ActionBase

class ComboRow(GenerativeUI[BaseComboRowItem]):
    def __init__(self, action_base: "ActionBase",
                 var_name: str,
                 default_value: int,
                 items: list[BaseComboRowItem],
                 on_change: callable = None,
                 title: str = None,
                 subtitle: str = None,
                 enable_search: bool = False,
                 ):
        super().__init__(action_base, var_name, default_value, on_change)

        self.widget: Combo = Combo(
            title=self.get_translation(title, title),
            subtitle=self.get_translation(subtitle, subtitle),
            items=items,
            enable_search=enable_search
        )

        self.widget.connect("notify::selected", self._value_changed)

        #self.widget.connect("changed", self._value_changed)

    def _value_changed(self, combo_row: Combo, _):
        item = combo_row.get_selected_item()
        index = combo_row.get_selected()

        self._handle_value_changed(item, index)

    def _handle_value_changed(self, item: BaseComboRowItem, index: int):
        self.set_value(index)

        if self.on_change:
            self.on_change(self.widget, item)
    
    def set_ui_value(self, value: int):
        self.widget.set_selected(value)