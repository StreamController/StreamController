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
import gi
from fuzzywuzzy import fuzz

from GtkHelper.GtkHelper import BetterExpander
from src.backend.DeckManagement.InputIdentifier import InputIdentifier
from src.backend.PluginManager.ActionHolder import ActionHolder
from src.backend.PluginManager.ActionHolderGroup import ActionHolderGroup
from src.backend.PluginManager.ActionInputSupport import ActionInputSupport
from src.windows.mainWindow.elements.Sidebar.elements.ActionChooserParts.PluginActionRow import (
    PluginActionRow,
)

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk


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
