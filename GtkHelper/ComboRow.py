import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, Gio, GObject

from loguru import logger as log

class BaseComboRowItem(GObject.GObject):
    def __init__(self):
        super().__init__()

    def __str__(self):
        pass

    @GObject.Property(type=GObject.TYPE_STRING)
    def filter_value(self):
        return self.__str__()

class ComboRowItem(BaseComboRowItem):
    def __init__(self, label: str):
        super().__init__()
        self.label = label

    def __str__(self):
        return self.label

class ComboRow(Adw.ComboRow):
    """
        Initializes a new ComboRow widget with a list of items, allowing for search functionality and a default selection.

        Parameters:
            items (list[BaseComboRowItem]): A list of ComboRowItems (or subclasses) to populate the combo row.
            title (str, optional): The title to display in the combo row.
            subtitle (str, optional): The subtitle to display below the title.
            enable_search (bool, optional): Whether to enable the search functionality for filtering items in the combo row (default is True).
            default_selection (int, optional): The index of the item to be selected by default (default is 0).

        Description:
            This constructor sets up a ComboRow with the given list of items, allowing for interaction with the row
            via search functionality and item selection. It connects a signal list item factory to customize the appearance
            and behavior of the list items. The combo row’s model is populated with the given items, and the default
            selection is set based on the provided index.

            The method also sets up the filter expression for the search functionality and adds the items to the combo row.
            The combo row will automatically highlight the item at the provided default selection index.
    """
    def __init__(self,
                 items: list[BaseComboRowItem] | list[str],
                 title: str = None,
                 subtitle: str = None,
                 enable_search: bool = True,
                 default_selection: BaseComboRowItem = None):
        super().__init__(title=title, subtitle=subtitle)

        self.model = Gio.ListStore(item_type=GObject.GObject)

        factory = Gtk.SignalListItemFactory()
        factory.connect("setup", self._on_factory_setup)
        factory.connect("bind", self._on_factory_bind)

        self.set_model(self.model)
        self.set_factory(factory)

        self.set_enable_search(enable_search)
        self.set_expression(Gtk.PropertyExpression.new(BaseComboRowItem, None, "filter_value"))

        self.populate(self.convert_item_list(items), default_selection)

    def convert_item_list(self, items):
        converted_list: list[BaseComboRowItem] = []

        for item in items:
            if isinstance(item, str):
                converted_list.append(ComboRowItem(item))
            if isinstance(item, BaseComboRowItem):
                converted_list.append(item)

        return converted_list

    def set_selected_item(self, item: BaseComboRowItem | str):
        selected_item_index = 0
        for index in range(self.model.get_n_items()):
            if str(self.model.get_item(index)) == str(item):
                selected_item_index = index
                break

        self.set_selected(selected_item_index)
        return self.get_item_at(selected_item_index)

    def add_item(self, combo_row_item: BaseComboRowItem | str):
        if isinstance(combo_row_item, str):
            combo_row_item = ComboRowItem(combo_row_item)

        self.model.append(combo_row_item)

    def add_items(self, items: list[BaseComboRowItem] | list[str]):
        converted_list = self.convert_item_list(items)

        self.model.splice(self.model.get_n_items(), 0, converted_list)

    def remove_item_at_index(self, index: int):
        size = self.model.get_n_items()

        if not (0 <= index < size):
            log.error(f"Not able to remove Item at index: {index}. Out of range!")
            return

        self.model.remove(index)

    def remove_item(self, item: BaseComboRowItem | str):
        for index in range(self.model.get_n_items()):
            if str(self.model.get_item(index)) == str(item):
                self.remove_item_at_index(index)
                break

    def remove_items(self, start: int, amount: int):
        size = self.model.get_n_items()

        if not (0 <= start < size and start + amount < size):
            log.error("Not able to remove Items!")
            return

        for i in range(amount + 1):
            self.model.remove(start)

    def remove_all_items(self):
        self.model.remove_all()

    def get_item_at(self, index: int) -> BaseComboRowItem:
        return self.model.get_item(index)

    def get_item(self, name: str) -> BaseComboRowItem | None:
        for item in range(self.model.get_n_items()):
            item = self.model.get_item(item)
            if item and str(item) == name:
                return item
        return None

    def get_selected_item(self) -> BaseComboRowItem | None:
        selected_index = self.get_selected()

        if selected_index == -1:
            return None

        return self.get_item_at(selected_index)

    def populate(self, items: list[BaseComboRowItem], selected_item: BaseComboRowItem | str = ""):
        self.remove_all_items()
        self.add_items(items)
        self.set_selected_item(selected_item)

    def _on_factory_setup(self, factory, list_item):
        label = Gtk.Label(halign=Gtk.Align.START)
        list_item.set_child(label)

    def _on_factory_bind(self, factory, list_item):
        item = list_item.get_item()
        label = list_item.get_child()
        label.set_text(str(item))