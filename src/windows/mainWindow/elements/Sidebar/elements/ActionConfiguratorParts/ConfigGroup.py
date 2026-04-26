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

from src.backend.PluginManager.ActionCore import ActionCore

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw


class ConfigGroup(Adw.PreferencesGroup):
    def __init__(self, parent, **kwargs):
        super().__init__(**kwargs)
        self.parent = parent
        self.loaded_rows = []
        self.build()

    def build(self):
        pass

    def load_for_action(self, action: ActionCore):
        config_rows = action.get_config_rows()
        generative_ui_objects = action.get_generative_ui()

        if not config_rows and not generative_ui_objects:
            self.hide()
            return

        # Load labels
        self.set_title(action.action_name)
        self.set_description(action.plugin_base.plugin_name)

        # Clear
        self.clear()

        def load_config_rows():
            # Load rows
            for row in config_rows:
                self.add(row)
                self.loaded_rows.append(row)

        def load_gen_ui_rows():
            for gen_ui in generative_ui_objects:
                gen_ui.load_ui_value()

                if not gen_ui.auto_add:
                    continue

                widget = gen_ui.widget

                if widget.get_parent() is not None:
                    continue

                self.add(widget)
                self.loaded_rows.append(widget)

        if action.put_custom_config_rows_below_gen_ui:
            load_gen_ui_rows()
            load_config_rows()
        else:
            load_config_rows()
            load_gen_ui_rows()
        
        # Show
        self.show()

    def clear(self):
        for row in self.loaded_rows:
            self.remove(row)
        self.loaded_rows = []
