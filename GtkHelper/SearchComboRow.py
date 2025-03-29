"""
Author: t00m
Year: 2022
Link: https://discourse.gnome.org/t/example-of-gtk-dropdown-with-search-enabled-without-gtk-expression/12748
Modified by: G4PLS
Modified the Original code to fit the purpose of this application.
"""

from typing_extensions import deprecated
import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, Gio, GObject

from loguru import logger as log

@deprecated("This has been deprecated in favor of GtkHelper.ComboRow")
class SearchComboRowItem(GObject.Object):
    __gtype_name__ = 'SearchComboRowItem'

    def __init__(self, display_label):
        super().__init__()
        self._display_label = display_label

    @GObject.Property
    def display_label(self):
        return self._display_label

@deprecated("This has been deprecated in favor of GtkHelper.ComboRow")
class SearchComboRow(Adw.PreferencesRow):
    __gtype_name__ = "SearchComboRow"
    __gsignals__ = {
        'item-changed': (GObject.SignalFlags.RUN_FIRST, None, (SearchComboRowItem, int,)),
    }

    def __init__(self, title: str, use_single_line: bool = False, *args, **kwargs):
        super().__init__(title=title, *args, **kwargs)
        self.search_text = '' # Initial search text for widgets

        # Setup DropDown for Widgets
        ## Create model
        self.model_widget = Gio.ListStore(item_type=SearchComboRowItem)
        self.sort_model_widget  = Gtk.SortListModel(model=self.model_widget) # FIXME: Gtk.Sorter?
        self.filter_model_widget = Gtk.FilterListModel(model=self.sort_model_widget)
        self.filter_widget = Gtk.CustomFilter.new(self._do_filter_widget_view, self.filter_model_widget)
        self.filter_model_widget.set_filter(self.filter_widget)

        ## Create factory
        factory_widget = Gtk.SignalListItemFactory()
        factory_widget.connect("setup", self._on_factory_widget_setup)
        factory_widget.connect("bind", self._on_factory_widget_bind)

        ## Create DropDown
        self.dropdown = Gtk.DropDown(model=self.filter_model_widget, factory=factory_widget)
        self.dropdown.set_enable_search(True)
        self.dropdown.connect("notify::selected-item", self._on_selected_widget)

        ## Get SearchEntry
        search_entry_widget = self._get_search_entry_widget(self.dropdown)
        search_entry_widget.connect('search-changed', self._on_search_widget_changed)

        # Setup main window
        if not use_single_line:
            self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12, hexpand=True, vexpand=False)
        else:
            self.main_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12, hexpand=True, vexpand=False)
        self.main_box.props.margin_start = 12
        self.main_box.props.margin_end = 12
        self.main_box.props.margin_top = 6
        self.main_box.props.margin_bottom = 6

        self.set_child(self.main_box)
        self.label = Gtk.Label(label=title, hexpand=True, xalign=0)
        self.main_box.append(self.label)
        self.main_box.append(self.dropdown)

    def _get_search_entry_widget(self, dropdown):
        popover = dropdown.get_last_child()
        box = popover.get_child()
        box2 = box.get_first_child()
        search_entry = box2.get_first_child() # Gtk.SearchEntry
        return search_entry

    def _on_factory_widget_setup(self, factory, list_item):
        box = Gtk.Box(spacing=6, orientation=Gtk.Orientation.HORIZONTAL)
        label = Gtk.Label()
        box.append(label)
        list_item.set_child(box)

    def _on_factory_widget_bind(self, factory, list_item):
        box = list_item.get_child()
        label = box.get_first_child()
        widget = list_item.get_item()
        label.set_text(widget.display_label)

    def _on_selected_widget(self, dropdown, data):
        selection = dropdown.get_selected_item()
        index = dropdown.get_selected()

        if selection and index >= 0:
            self.emit("item-changed", selection, index)

    def _on_search_widget_changed(self, search_entry):
        self.search_text = search_entry.get_text()
        self.filter_widget.changed(Gtk.FilterChange.DIFFERENT)

    def _do_filter_widget_view(self, item, filter_list_model):
        return self.search_text.upper() in item.display_label.upper()

    def populate(self, list: list[SearchComboRowItem], selected_index: int = 0):
        self.model_widget.remove_all()

        for item in list:
            self.model_widget.append(item)

        self.dropdown.set_selected(selected_index)

    def set_selected_item(self, index: int):
        if index < 0:
            return

        try:
            self.dropdown.set_selected(index)
        except Exception as e:
            log.error(e)
