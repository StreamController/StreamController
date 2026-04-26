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

import globals as gl
from GtkHelper.GtkHelper import BetterPreferencesGroup
from src.backend.DeckManagement.InputIdentifier import InputIdentifier
from src.windows.mainWindow.elements.Sidebar.elements.ActionChooserParts.Expanders import (
    PluginExpander,
)

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")


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
