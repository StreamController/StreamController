"""
Author: Core447
Year: 2023

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
any later version.

This programm comes with ABSOLUTELY NO WARRANTY!

You should have received a copy of the GNU General Public License
along with this program. If not, see <https://www.gnu.org/licenses/>.
"""
# Import gtk modules
import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw

# Import Python modules
from loguru import logger as log
from fuzzywuzzy import fuzz, process

# Import own modules
from src.backend.DeckManagement.HelperMethods import get_last_dir
from GtkHelper.GtkHelper import BetterExpander, BetterPreferencesGroup
from src.windows.Store.Store import Store
from src.backend.PluginManager.ActionHolder import ActionHolder

# Import typing
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from src.windows.mainWindow.elements.Sidebar import Sidebar

# Import globals
import globals as gl

class ActionChooser(Gtk.Box):
    def __init__(self, sidebar: "Sidebar", **kwargs):
        super().__init__(hexpand=True, vexpand=True, **kwargs)
        self.sidebar: "Sidebar" = sidebar

        self.callback_function = None
        self.callback_args = None
        self.callback_kwargs = None

        self.build()

    def build(self):
        self.scrolled_window = Gtk.ScrolledWindow(hexpand=True, vexpand=True)
        self.append(self.scrolled_window)

        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, hexpand=True, vexpand=True, margin_top=4, margin_start=25, margin_end=25)
        self.scrolled_window.set_child(self.main_box)

        self.nav_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, hexpand=True)
        self.main_box.append(self.nav_box)

        self.back_button = Gtk.Button(icon_name="back")
        self.back_button.connect("clicked", self.on_back_button_click)
        self.nav_box.append(self.back_button)

        self.back_label = Gtk.Label(label=gl.lm.get("action-chooser.go-back.label"), margin_start=6, xalign=0, css_classes=["bold"])
        self.nav_box.append(self.back_label)

        self.search_entry = Gtk.SearchEntry(margin_top=10, placeholder_text=gl.lm.get("action-chooser.search-entry.placeholder"), hexpand=True)
        self.search_entry.connect("search-changed", self.on_search_changed)
        self.main_box.append(self.search_entry)

        self.header = Gtk.Label(label=gl.lm.get("action-chooser.header"), xalign=0, css_classes=["page-header"], margin_start=20, margin_top=30)
        self.main_box.append(self.header)

        self.plugin_group = PluginGroup(self, margin_top=40)
        self.main_box.append(self.plugin_group)

        self.open_store_button = OpenStoreButton(margin_top=40)
        self.main_box.append(self.open_store_button)

    def show(self, callback_function, current_stack_page, callback_args, callback_kwargs):
        # The current-stack_page is usefull in case the let_user_select_action is called by an plugin action in the action_configurator

        # Validate the callback function
        if not callable(callback_function):
            log.error(f"Invalid callback function: {callback_function}")
            self.callback_function = None
            self.callback_args = None
            self.callback_kwargs = None
            self.current_stack_page = None
            return
        
        self.callback_function = callback_function
        self.current_stack_page = current_stack_page
        self.callback_args = callback_args
        self.callback_kwargs = callback_kwargs

        self.sidebar.main_stack.set_visible_child(self)

    def on_back_button_click(self, button):
        self.sidebar.main_stack.set_visible_child_name("key_editor")

    def on_search_changed(self, search_entry):
        self.plugin_group.search()


class OpenStoreButton(Gtk.Button):
    def __init__(self, *args, **kwargs):
        super().__init__(label="Get More", css_classes=["open-store-button"],
                         *args, **kwargs)
        self.connect("clicked", self.on_click)

    def on_click(self, button):
        self.store = Store(application=gl.app, main_window=gl.app.main_win)
        self.store.present()

class PluginGroup(BetterPreferencesGroup):
    def __init__(self, action_chooser, **kwargs):
        super().__init__(**kwargs)
        self.action_chooser = action_chooser

        self.expander = []

        self.update()

        self.set_sort_func(self.sort_func, None)
        self.set_filter_func(self.filter_func, None)

    def update(self):
        self.clear()
        self.expander = []
        for plugin_name, plugin_dir in gl.plugin_manager.get_plugins().items():
            expander = PluginExpander(self, plugin_name, plugin_dir)
            self.add(expander)
            self.expander.append(expander)

    def search(self):
        # Let the expanders search
        for expander in self.expander:
            expander.search()

        self.invalidate_sort()
        self.invalidate_filter()

    def sort_func(self, expander1, expander2, user_data):
        search_string = self.action_chooser.search_entry.get_text()

        if search_string == "":
            # sort alphabetically
            if expander1.get_title() < expander2.get_title():
                return -1
            if expander1.get_title() > expander2.get_title():
                return 1
            return 0

        highest_fuzz_1 = expander1.highest_fuzz_score
        highest_fuzz_2 = expander2.highest_fuzz_score

        title_fuzz_1 = fuzz.ratio(search_string.lower(), expander1.get_title().lower())
        title_fuzz_2 = fuzz.ratio(search_string.lower(), expander2.get_title().lower())

        # Sort by highest fuzzy score and title fuzz score
        max_expander_1 = max(highest_fuzz_1, title_fuzz_1)
        max_expander_2 = max(highest_fuzz_2, title_fuzz_2)

        if max_expander_1 > max_expander_2:
            return -1
        elif max_expander_1 < max_expander_2:
            return 1
        
        return 0
    
    def filter_func(self, expander, user_data):
        MIN_ACTION_FUZZY_SCORE = 20
        MIN_TITLE_FUZZY_SCORE = 20

        search_string = self.action_chooser.search_entry.get_text()
        if search_string == "":
            # Show all
            return True

        if expander.highest_fuzz_score >= MIN_ACTION_FUZZY_SCORE:
            return True
        
        title_fuzzy = fuzz.ratio(search_string.lower(), expander.get_title().lower())
        if title_fuzzy >= MIN_TITLE_FUZZY_SCORE:
            return True
        return False


class PluginExpander(BetterExpander):
    def __init__(self, plugin_group, plugin_name, plugin_dir, **kwargs):
        super().__init__(**kwargs)
        self.plugin_group = plugin_group
        self.plugin_name = plugin_name
        self.plugin_dir = plugin_dir

        # Texts
        self.set_title(plugin_name)
        self.set_subtitle(get_last_dir(plugin_dir["folder-path"]))

        self.add_prefix(self.plugin_dir["object"].get_selector_icon())

        action_holders: list[ActionHolder] = self.plugin_dir["object"].action_holders.values()
        for holder in action_holders:
            action_row = ActionRow(self, holder)
            self.add_row(action_row)

        self.highest_fuzz_score = 0

        # Init sort func
        self.set_sort_func(self.sort_func, None)
        # Init filter func
        self.set_filter_func(self.filter_func, None)

    def search(self):
        self.invalidate_filter()
        self.invalidate_sort()

    def sort_func(self, row1, row2, user_data):
        # Returns -1 if row1 should be brefore row2, 0 if they are equal, and 1 otherwise
        search_string = self.plugin_group.action_chooser.search_entry.get_text()

        action1_label = row1.label.get_label()
        action2_label = row2.label.get_label()

        if search_string == "":
            self.highest_fuzz_score = 0
            # sort alphabetically
            if action1_label < action2_label:
                return -1
            if action1_label > action2_label:
                return 1
            return 0

        fuzz_score_1 = fuzz.ratio(search_string.lower(), action1_label.lower())
        fuzz_score_2 = fuzz.ratio(search_string.lower(), action2_label.lower())

        if fuzz_score_1 > self.highest_fuzz_score:
            self.highest_fuzz_score = fuzz_score_1
        if fuzz_score_2 > self.highest_fuzz_score:
            self.highest_fuzz_score = fuzz_score_2

        if fuzz_score_1 > fuzz_score_2:
            return -1
        if fuzz_score_1 < fuzz_score_2:
            return 1
        return 0
    
    def filter_func(self, row, user_data):
        search_string = self.plugin_group.action_chooser.search_entry.get_text()

        if search_string == "":
            # Collapse all
            self.set_expanded(False)
            # Show all
            return True

        fuzz_score = fuzz.ratio(search_string.lower(), row.label.get_label().lower())

        MIN_FUZZY_SCORE = 20
        if fuzz_score >= MIN_FUZZY_SCORE:
            # Expand
            self.set_expanded(True)
            return True
        return False


class ActionRow(Adw.PreferencesRow):
    def __init__(self, expander, action_holder: ActionHolder, **kwargs):
        super().__init__(**kwargs)
        self.expander = expander
        self.action_holder = action_holder

        self.button = Gtk.Button(hexpand=True, vexpand=True, overflow=Gtk.Overflow.HIDDEN,
                                 css_classes=["no-margin", "invisible"])
        self.button.connect("clicked", self.on_click)
        self.set_child(self.button)
        
        self.main_box = Gtk.Box(hexpand=True, vexpand=True, orientation=Gtk.Orientation.HORIZONTAL,
                                margin_top=10, margin_bottom=10)
        self.button.set_child(self.main_box)

        # self.icon = Gtk.Image(icon_name="insert-image", icon_size=Gtk.IconSize.LARGE, margin_start=5)
        self.icon = action_holder.icon
        if action_holder.icon.get_parent() is not None:
            self.action_holder.icon.get_parent().remove(self.action_holder.icon)
        self.main_box.append(self.icon)

        self.label = Gtk.Label(label=self.action_holder.action_name, margin_start=10, css_classes=["bold", "large-text"])
        self.main_box.append(self.label)

    def on_click(self, button):
        if self.action_holder.action_base == None:
            return
        
        # Go back to old page
        self.expander.plugin_group.action_chooser.sidebar.main_stack.set_visible_child(self.expander.plugin_group.action_chooser.current_stack_page)

        # Verify the callback function
        if not callable(self.expander.plugin_group.action_chooser.callback_function):
            log.warning(f"Invalid callback function: {self.expander.plugin_group.action_chooser.callback_function}")
            return
        
        # Call the callback function
        callback = self.expander.plugin_group.action_chooser.callback_function
        args = self.expander.plugin_group.action_chooser.callback_args
        kwargs = self.expander.plugin_group.action_chooser.callback_kwargs

        
        callback(self.action_holder, *args, **kwargs)