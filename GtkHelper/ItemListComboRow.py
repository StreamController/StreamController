"""
Author: GsakuL
Year: 2024

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
any later version.

This programm comes with ABSOLUTELY NO WARRANTY!

You should have received a copy of the GNU General Public License
along with this program. If not, see <https://www.gnu.org/licenses/>.
"""

from typing import Sequence

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, Gio, GObject

from loguru import logger as log


class ItemListComboRowListItem(GObject.Object):
    def __init__(self, key: str, name: str):
        super().__init__()
        self._key = key
        self._name = name

    @GObject.Property(type=str)
    def key(self):
        return self._key
    
    @GObject.Property(type=str)
    def name(self):
        return self._name


class ItemListComboRow(Adw.ComboRow):
    """
    A primitive wrapper, to make simple "combo box"-style selections.
    You likely want to `.connect("notify::selected", ...)`, and then call `get_selected_item()` there,
    to get the ListItem (key-name-pair) again

    Based on https://discourse.gnome.org/t/migrate-from-comboboxtext-to-comborow-dropdown/10565/2
    """

    def __init__(self, items: Sequence[ItemListComboRowListItem], *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.__items: list[ItemListComboRowListItem] = list(items)
        self.model = Gio.ListStore(item_type=ItemListComboRowListItem)
        self.factory = Gtk.SignalListItemFactory()

        self.set_items(items)

        self.factory.connect("setup", self.__on_factory_setup)
        self.factory.connect("bind", self.__on_factory_bind)

        self.set_model(self.model)
        self.set_factory(self.factory)

    def set_items(self, items: Sequence[ItemListComboRowListItem]):
        self.model.remove_all()
        keys = set()
        self.__items = list(items)
        for i in self.__items:
            if i.key in keys:
                raise ValueError(f"key '{i.key}' was given more than once in item list")
            keys.add(i.key)
            self.model.append(i)

        self.set_model(self.model) # Update ui

    def __on_factory_setup(self, factory, list_item):
        label = Gtk.Label()
        list_item.set_child(label)

    def __on_factory_bind(self, factory, list_item):
        label = list_item.get_child()
        entry: ItemListComboRowListItem = list_item.get_item()
        label.set_text(entry.name)

    def set_selected_item_by_key(self, key: str, default: int | None = None):
        """
        Call when loading user-settings, to pre-select the correkt ListItem
        """
        index_ = next((i for i, t in enumerate(self.__items) if t.key == key), default)
        if index_ is None:
            log.warning("key '{0}' was not found amongst item list, and no default was given", key)
            
        if isinstance(index_, int):
            if index_ is not None:
                if index_ >= 0 and index_ < len(self.__items):
                    self.set_selected(index_)
                    return
        
        self.set_selected(Gtk.INVALID_LIST_POSITION)