from GtkHelper.ComboRow import ComboRow as Combo, BaseComboRowItem
from GtkHelper.GenerativeUI.GenerativeUI import GenerativeUI

import gi
from gi.repository import Gtk, Adw

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from src.backend.PluginManager import ActionBase

from GtkHelper.GtkHelper import better_disconnect


class ComboRow(GenerativeUI[BaseComboRowItem]):
    """
    A UI element representing a combo box (drop-down menu) with selectable items,
    linked to an `ActionBase` instance.

    Attributes:
        _widget (Combo): The ComboRow widget instance.
    """

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
        """
        Initializes the ComboRow UI element.

        Args:
            action_base (ActionBase): The associated action instance.
            var_name (str): The variable name for storing the selected value.
            default_value (BaseComboRowItem | str): The default selected item.
            items (list[BaseComboRowItem] | list[str]): The list of selectable items.
            title (str, optional): The title of the combo box. Defaults to None.
            subtitle (str, optional): The subtitle of the combo box. Defaults to None.
            enable_search (bool, optional): Enables search functionality. Defaults to False.
            on_change (callable, optional): Callback triggered when selection changes. Defaults to None.
            can_reset (bool, optional): Whether resetting is allowed. Defaults to True.
            auto_add (bool, optional): Whether to automatically add this UI element to the action. Defaults to True.
        """
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
        """Connects the signal to detect selection changes in the combo box."""
        self.widget.connect("notify::selected", self._value_changed)

    def disconnect_signals(self):
        """Disconnects the signal for selection changes."""
        better_disconnect(self.widget, self._value_changed)

    def _value_changed(self, combo_row: Combo, _):
        """Handles the event when a new item is selected."""
        item = combo_row.get_selected_item()
        self._handle_value_changed(item)

    def _handle_value_changed(self, item: BaseComboRowItem):
        """Handles updating the stored value and triggering the change callback."""
        old_value = self.get_value(self._default_value)
        old_value = self.get_item(old_value)

        self.set_value(str(item))

        if self.on_change:
            self.on_change(self.widget, item, old_value)

    @GenerativeUI.signal_manager
    def set_ui_value(self, value: BaseComboRowItem | str):
        """Sets the selected item in the UI."""
        self.widget.set_selected_item(value)

    # Widget Wrappers

    def set_selected_item(self, item: BaseComboRowItem | str = "", update_setting: bool = False):
        """Sets the selected item and optionally updates the stored value."""
        self.set_ui_value(item)

        if update_setting:
            self.set_value(str(item))

    @GenerativeUI.signal_manager
    def add_item(self, combo_row_item: BaseComboRowItem | str):
        """Adds a single item to the combo box."""
        self.widget.add_item(combo_row_item)

    @GenerativeUI.signal_manager
    def add_items(self, items: list[BaseComboRowItem] | list[str]):
        """Adds multiple items to the combo box."""
        self.widget.add_items(items)

    @GenerativeUI.signal_manager
    def remove_item_at_index(self, index: int):
        """Removes an item from the combo box by its index."""
        self.widget.remove_item_at_index(index)

    @GenerativeUI.signal_manager
    def remove_item(self, item: BaseComboRowItem | str):
        """Removes an item from the combo box by its value."""
        self.widget.remove_item(item)

    @GenerativeUI.signal_manager
    def remove_items(self, start: int, amount: int):
        """Removes a range of items from the combo box."""
        self.widget.remove_items(start, amount)

    @GenerativeUI.signal_manager
    def remove_all_items(self):
        """Clears all items from the combo box."""
        self.widget.remove_all_items()

    def get_item_at(self, index: int) -> BaseComboRowItem:
        """Retrieves an item at a specific index."""
        return self.widget.get_item_at(index)

    def get_item(self, name: str) -> BaseComboRowItem:
        """Retrieves an item by its name."""
        return self.widget.get_item(name)

    def get_selected_item(self) -> BaseComboRowItem | None:
        """Returns the currently selected item."""
        return self.widget.get_selected_item()

    @GenerativeUI.signal_manager
    def populate(self, items: list[BaseComboRowItem] | list[str], selected_item: BaseComboRowItem | str = "",
                 update_setting: bool = False):
        """Repopulates the combo box with new items and optionally updates the selection."""
        self.remove_all_items()
        self.add_items(items)
        self.set_selected_item(selected_item)

        if update_setting:
            self.set_value(str(self.get_selected_item()))

        self.update_value_in_ui()