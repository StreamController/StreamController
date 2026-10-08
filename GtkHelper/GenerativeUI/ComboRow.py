from GtkHelper.ComboRow import ComboRow as Combo, BaseComboRowItem, ComboRowItem
from GtkHelper.GenerativeUI.GenerativeUI import GenerativeUI

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from src.backend.PluginManager.ActionCore import ActionCore

from GtkHelper.GtkHelper import better_disconnect


class ComboRow(GenerativeUI[BaseComboRowItem]):
    """
    A UI element representing a combo box (drop-down menu) with selectable items,
    linked to an `ActionCore` instance.

    Attributes:
        _widget (Combo): The ComboRow widget instance.
    """

    def __init__(self,
                 action_core: "ActionCore",
                 var_name: str,
                 default_value: BaseComboRowItem | str,
                 items: list[BaseComboRowItem] | list[str],
                 title: str = None,
                 subtitle: str = None,
                 enable_search: bool = False,
                 on_change: callable = None,
                 can_reset: bool = True,
                 auto_add: bool = True,
                 complex_var_name: bool = False
                 ):
        """
        Initializes the ComboRow UI element.

        Args:
            action_core (ActionCore): The associated action instance.
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
        super().__init__(action_core, var_name, default_value, can_reset, auto_add, complex_var_name, on_change)

        self._widget: Combo = Combo(
            title=self.get_translation(title, title),
            subtitle=self.get_translation(subtitle, subtitle),
            items=items,
            enable_search=enable_search,
            default_selection=self._default_value
        )

        self._handle_reset_button_creation()
        self.connect_signals()

    @GenerativeUI.signal_manager
    def set_sensitive(self, sensitive: bool):
        self.widget.set_sensitive(sensitive)

    def get_sensitive(self):
        return self.widget.get_sensitive()

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

    def _handle_value_changed(self, item: BaseComboRowItem, update_settings: bool = True, trigger_callback: bool = True):
        """Handles updating the stored value and triggering the change callback."""
        old_value = self.get_value(self._default_value)

        if update_settings and item is not None:
            self.set_value(item)

        if trigger_callback and self.on_change:
            # Look the previous value up in the model, but fall back to the stored value itself.
            # A stored value that is not (yet) in the model must not be reported as None, otherwise
            # on_change handlers cannot tell a real user change from a reload.
            old_item = self.get_item(old_value)
            if old_item is None and old_value not in (None, ""):
                old_item = ComboRowItem(str(old_value))

            self.on_change(self.widget, item, old_item)

    @GenerativeUI.signal_manager
    def reset_value(self):
        selected_item = self.widget.set_selected_item(self._default_value)
        if selected_item is None and self._default_value not in (None, ""):
            # The default may not be in the model - store it anyway, a reset is an explicit user
            # action. Keep the declared item as it is so its get_value() is persisted; only a
            # plain string needs wrapping so callbacks always receive a BaseComboRowItem.
            if isinstance(self._default_value, BaseComboRowItem):
                selected_item = self._default_value
            else:
                selected_item = ComboRowItem(str(self._default_value))
        self._handle_value_changed(selected_item)

    @GenerativeUI.signal_manager
    def load_initial_ui(self):
        """
        Restore the UI from the stored value.

        Restoring must be strictly read-only with respect to the settings: signals are disconnected
        so that notify::selected cannot write the restored (or a fallback) value back, and
        _handle_value_changed() is told not to update them either. The on_change callback still
        runs, like it does for every other generative UI element, because plugins use it to
        initialize dependent widgets.
        """
        value = self.get_value()
        selected_item = self.widget.set_selected_item(value)

        if selected_item is None and value not in (None, ""):
            # The stored value is not in the model yet - the combo is usually filled later, from a
            # plugin backend. Report the stored value rather than None so on_change handlers see a
            # no-op restore instead of what looks like the user clearing the selection.
            selected_item = ComboRowItem(str(value))

        self._handle_value_changed(selected_item, update_settings=False)

    @GenerativeUI.signal_manager
    def set_ui_value(self, value: BaseComboRowItem | str):
        """Sets the selected item in the UI."""
        self.widget.set_selected_item(value)

    def set_value(self, item: BaseComboRowItem | str):
        """Sets the selected item in the UI."""

        if isinstance(item, BaseComboRowItem):
            value = item.get_value()
        else:
            value = item

        super().set_value(value)

    # Widget Wrappers

    @GenerativeUI.signal_manager
    def set_selected_item(self, item: BaseComboRowItem | str = "", update_setting: bool = False,
                          fallback_to_first: bool = False):
        """
        Sets the selected item and optionally updates the stored value.

        Signal managed like every other operation that changes the widget: without it the change
        would emit notify::selected, and when the call is dispatched from another thread that
        emission arrives after the caller is long gone - persisting a selection the user never
        made. Off the main thread the decorator returns None, which callers already treat as
        "nothing selected" and therefore never write.
        """
        selected_item = self.widget.set_selected_item(item, fallback_to_first=fallback_to_first)

        if update_setting and selected_item is not None:
            self.set_value(selected_item)

        return selected_item

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

    def get_item_amount(self):
        return self.widget.get_item_amount()

    @GenerativeUI.signal_manager
    def populate(self, items: list[BaseComboRowItem] | list[str], selected_item: BaseComboRowItem | str = "",
                 update_settings: bool = False,
                 trigger_callback: bool = True,
                 fallback_to_first: bool = False):
        """
        Repopulates the combo box with new items and optionally updates the selection.

        Refilling the model and deciding on the selection has to happen as one uninterrupted step:
        whether the requested value is a fallback is decided by reading the model back. The
        decorator keeps the whole method on the main thread, so those reads always see the model
        this call just built rather than a half applied one.
        """
        self.widget.remove_all_items()
        self.widget.add_items(items)

        # Whether the requested value really is in the new model - a fallback selection is a purely
        # visual affordance and must never be written to the settings
        # An explicitly empty selection is a deliberate clear, not a fallback
        is_fallback = bool(selected_item) and self.widget.get_item(selected_item) is None
        selected_item = self.widget.set_selected_item(selected_item, fallback_to_first=fallback_to_first)

        self._handle_value_changed(selected_item, update_settings and not is_fallback, trigger_callback)
        if selected_item is not None:
            # Re-apply the selection, the callback above may have changed it. Never re-run the
            # fallback here, that would select the first item for a value that is not in the model.
            self.widget.set_selected_item(selected_item)