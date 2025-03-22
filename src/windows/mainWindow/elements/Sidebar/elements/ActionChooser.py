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
from re import I
import gi

from src.backend.DeckManagement.InputIdentifier import Input, InputIdentifier
from src.backend.PluginManager.ActionHolderGroup import ActionHolderGroup
from src.backend.PluginManager.ActionInputSupport import ActionInputSupport

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw

# Import Python modules
from loguru import logger as log
from fuzzywuzzy import fuzz, process

# Import own modules
from src.backend.DeckManagement.HelperMethods import get_last_dir
from GtkHelper.GtkHelper import BackButton, BetterExpander, BetterPreferencesGroup, better_disconnect
from src.windows.Store.Store import Store
from src.backend.PluginManager.ActionHolder import ActionHolder

# Import typing
from typing import TYPE_CHECKING, Type
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
        self.identifier: InputIdentifier = None

        self.build()

    def build(self):
        self.scrolled_window = Gtk.ScrolledWindow(hexpand=True, vexpand=True)
        self.append(self.scrolled_window)

        self.clamp = Adw.Clamp()
        self.scrolled_window.set_child(self.clamp)

        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, hexpand=True, vexpand=True, margin_top=4)
        self.clamp.set_child(self.main_box)

        self.nav_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, hexpand=True)
        self.main_box.append(self.nav_box)

        self.back_button = BackButton()
        self.back_button.connect("clicked", self.on_back_button_click)
        self.nav_box.append(self.back_button)

        self.header = Gtk.Label(label=gl.lm.get("action-chooser.header"), xalign=0, css_classes=["page-header"], margin_start=20, margin_top=30)
        self.main_box.append(self.header)

        self.search_entry = Gtk.SearchEntry(margin_top=10,
                                            placeholder_text=gl.lm.get("action-chooser.search-entry.placeholder"),
                                            hexpand=True)
        self.search_entry.connect("search-changed", self.on_search_changed)
        self.main_box.append(self.search_entry)

        self.plugin_group = PluginGroup(self, margin_top=40)
        self.main_box.append(self.plugin_group)

        self.open_store_button = OpenStoreButton(margin_top=40, margin_bottom=40)
        self.main_box.append(self.open_store_button)

    def show(self, callback_function, current_stack_page, identifier: InputIdentifier, callback_args, callback_kwargs):
        # The current-stack_page is usefull in case the let_user_select_action is called by an plugin action in the action_configurator

        # Validate the callback function
        if not callable(callback_function):
            log.error(f"Invalid callback function: {callback_function}")
            self.callback_function = None
            self.callback_args = None
            self.callback_kwargs = None
            self.current_stack_page = None
            self.identifier = None
            return
        
        self.callback_function = callback_function
        self.current_stack_page = current_stack_page
        self.callback_args = callback_args
        self.callback_kwargs = callback_kwargs
        self.identifier = identifier
        self.plugin_group.set_identifier(identifier)

        self.sidebar.main_stack.set_visible_child(self)

    def on_back_button_click(self, button):
        self.sidebar.main_stack.set_visible_child_name("configurator_stack")

    def on_search_changed(self, search_entry):
        self.plugin_group.search()

class OpenStoreButton(Gtk.Button):
    def __init__(self, *args, **kwargs):
        super().__init__(label=gl.lm.get("asset-chooser.add-more-button.label"), css_classes=["open-store-button"],
                         *args, **kwargs)
        self.connect("clicked", self.on_click)

    def on_click(self, button):
        gl.app.open_store()

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
        for plugin_id, plugin_dir in dict(gl.plugin_manager.get_plugins()).items():
            plugin_name = plugin_dir["object"].plugin_name
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
    
    def set_identifier(self, identifier: InputIdentifier):
        for expander in self.expander:
            expander.set_identifier(identifier)
            expander.invalidate_filter()

class ActionChooserExpander(BetterExpander):
    def __init__(self, plugin_group, plugin_name, plugin_dir, *args, **kwargs):
        super().__init__()
        self.plugin_group = plugin_group
        self.plugin_name = plugin_name
        self.plugin_dir = plugin_dir

        self.input_type: InputIdentifier = None

        self.highest_fuzz_score = 0

        self.set_sort_func(self.sort_func, None)
        self.set_filter_func(self.filter_func, None)

    def build(self):
        pass

    def sort_func(self, row1, row2, user_data):
        pass

    def filter_func(self, row: "PluginActionRow", user_data):
        pass

    def calculate_fuzz_ratio_sort(self, search_string, action1_label, action2_label):
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

    def calculate_fuzz_ratio_filter(self, search_string, label):
        if search_string == "":
            # Collapse all
            self.set_expanded(False)
            # Show all
            return True

        fuzz_score = fuzz.ratio(search_string.lower(), label.lower())

        MIN_FUZZY_SCORE = 20
        if fuzz_score >= MIN_FUZZY_SCORE:
            # Expand
            self.set_expanded(True)
            return True
        return False

    def search(self):
        self.invalidate_filter()
        self.invalidate_sort()

class PluginExpander(ActionChooserExpander):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.build()
        self.add_action_holders(*args, **kwargs)

    def build(self):
        # Texts
        self.set_title(self.plugin_name)
        self.set_subtitle(self.plugin_dir["object"].plugin_id)

        self.add_prefix(self.plugin_dir["object"].get_selector_icon())

    def add_action_holders(self, *args, **kwargs):
        action_holders: set[ActionHolder] = set(self.plugin_dir["object"].action_holders.values())
        action_holder_groups: set[ActionHolderGroup] = self.plugin_dir["object"].action_holder_groups

        added_holders: set[ActionHolder] = set()

        # Add Groups
        for group in action_holder_groups:
            action_group = ActionGroupExpander(group, *args, **kwargs)
            action_group.add_css_class("action-chooser-item")
            action_group.add_css_class("action-chooser-group")

            self.add_row(action_group)
            added_holders.update(group.get_action_holders())

        not_added_holders = action_holders - added_holders

        # Add leftovers
        for holder in not_added_holders:
            action_row = PluginActionRow(self, holder)
            action_row.add_css_class("action-chooser-item")

            self.add_row(action_row)

    def sort_func(self, row1, row2, user_data):
        # Returns -1 if row1 should be brefore row2, 0 if they are equal, and 1 otherwise
        search_string = self.plugin_group.action_chooser.search_entry.get_text()

        if type(row1) is Gtk.ListBoxRow or type(row2) is Gtk.ListBoxRow:
            return 0

        if isinstance(row1, ActionGroupExpander):
            action1_label = row1.get_title()
        else:
            action1_label = row1.label.get_label()

        if isinstance(row2, ActionGroupExpander):
            action2_label = row2.get_title()
        else:
            action2_label = row2.label.get_label()

        return self.calculate_fuzz_ratio_sort(search_string, action1_label, action2_label)
    
    def filter_func(self, row: "PluginActionRow", user_data):
        search_string = self.plugin_group.action_chooser.search_entry.get_text()
        
        if isinstance(row, ActionGroupExpander):
            label = row.get_title()
        else:
            label = row.label.get_label()

        return self.calculate_fuzz_ratio_filter(search_string, label)
    
    def set_identifier(self, input_type: InputIdentifier):
        self.input_type = input_type
        for row in self.get_rows():
            if isinstance(row, ActionGroupExpander):
                if not self.set_group_identifier(input_type, row.holder_group, row):
                    continue
            row.set_identifier(input_type)
        self.invalidate_filter()

    def set_group_identifier(self, input_type: InputIdentifier, group: ActionHolderGroup, row):
        return True
        ## In case we want to hide groups later
        group_input_compatibility = group.get_min_input_compatibility(input_type)

        if group_input_compatibility <= ActionInputSupport.UNSUPPORTED:
            row.hide()
            return False
        return True

class ActionGroupExpander(ActionChooserExpander):
    def __init__(self, holder_group, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.holder_group: ActionHolderGroup = holder_group
        self.build()
        self.add_action_holders()

    def build(self):
        # Texts
        self.set_title(self.holder_group.get_group_name())

        folder_icon = Gtk.Image.new_from_icon_name("folder-symbolic")
        self.add_prefix(folder_icon)

        # set icon to not activated
        image = self.get_arrow_image()
        image.set_css_classes(["expander-arrow-not-activated"])

        self.connect("notify::expanded", self.on_expanded)

        self.warning_icon = Gtk.Image(icon_name="dialog-warning-symbolic",
                                      hexpand=True, halign=Gtk.Align.END, margin_end=3, visible=False)
        self.add_suffix(self.warning_icon)

    def add_action_holders(self):
        for holder in self.holder_group.get_action_holders():
            action_row = PluginActionRow(self, holder)
            action_row.add_css_class("action-chooser-group-item")

            self.add_row(action_row)

    def on_expanded(self, *args):
        # This expander is nested in another expander causing the icon to be stuck at the expanded state - this fixes it
        image = self.get_arrow_image()
        if self.get_expanded():
            image.set_css_classes(["expander-arrow-activated"])
        else:
            image.set_css_classes(["expander-arrow-not-activated"])

    def sort_func(self, row1, row2, user_data):
        # Returns -1 if row1 should be brefore row2, 0 if they are equal, and 1 otherwise
        search_string = self.plugin_group.action_chooser.search_entry.get_text()

        action1_label = row1.label.get_label()
        action2_label = row2.label.get_label()

        return self.calculate_fuzz_ratio_sort(search_string, action1_label, action2_label)

    def filter_func(self, row: "PluginActionRow", user_data):
        search_string = self.plugin_group.action_chooser.search_entry.get_text()

        label = row.label.get_label()

        return self.calculate_fuzz_ratio_filter(search_string, label)

    def set_identifier(self, input_type: InputIdentifier):
        compatibility = self.holder_group.get_min_input_compatibility(input_type)

        def show_compatibility(show: bool = False, tooltip: str = None, icon_name: str = None):
            self.warning_icon.set_visible(show)

            if icon_name:
                self.warning_icon.set_from_icon_name(icon_name)

            if tooltip:
                self.set_tooltip_text(tooltip)
                if show:
                    self.warning_icon.set_tooltip_text(tooltip)

        if self.holder_group.get_min_input_compatibility(input_type) < ActionInputSupport.UNTESTED:
            warning_icon = "dialog-error-symbolic"
            tooltip_text = f"Some actions in this group are not compatible with {input_type.input_type}"
            show_warning = True
        elif self.holder_group.get_min_input_compatibility(input_type) == ActionInputSupport.UNTESTED:
            warning_icon = "dialog-warning-symbolic"
            tooltip_text = f"Some actions in this group might not be compatible with {input_type.input_type}"
            show_warning = True
        else:
            warning_icon = None
            tooltip_text = ""
            show_warning = False

        show_compatibility(show=show_warning, tooltip=tooltip_text, icon_name=warning_icon)

        self.input_type = input_type
        for row in self.get_rows():
            row.set_identifier(input_type)
        self.invalidate_filter()

class PluginActionRow(Adw.ActionRow):
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

        self.warning_icon = Gtk.Image(icon_name="dialog-warning-symbolic",
                                      hexpand=True, halign=Gtk.Align.END, margin_end=3, visible=False)
        self.main_box.append(self.warning_icon)

    def on_click(self, button):
        if self.action_holder.action_core == None:
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

    def show_warning(self, show: bool, tooltip: str = None):
        self.warning_icon.set_visible(show)

        if show and tooltip is not None:
            self.warning_icon.set_tooltip_text(tooltip)

    def set_identifier(self, identifier: InputIdentifier):
        action_input_compatibility = self.action_holder.get_input_compatibility(identifier)

        if action_input_compatibility <= ActionInputSupport.UNSUPPORTED:
            self.warning_icon.set_from_icon_name("dialog-error-symbolic")
            self.set_tooltip_text(f"Action is not compatible with {identifier.input_type}")
            self.show_warning(True)
            self.set_sensitive(False)
            
        elif action_input_compatibility == ActionInputSupport.UNTESTED:
            self.warning_icon.set_from_icon_name("dialog-warning-symbolic")
            self.warning_icon.set_tooltip_text(f"Action might not be compatible with {identifier.input_type}")
            self.set_tooltip_text("")
            self.show_warning(True)
            self.set_sensitive(True)

        elif action_input_compatibility >= ActionInputSupport.SUPPORTED:
            self.set_tooltip_text("")
            self.show_warning(False)
            self.set_sensitive(True)