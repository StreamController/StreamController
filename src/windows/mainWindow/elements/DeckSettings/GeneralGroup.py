"""
Author: Core447
Year: 2025

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

from GtkHelper.GtkHelper import better_disconnect
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw

# Import globals
import globals as gl

class GeneralGroup(Adw.PreferencesGroup):
    def __init__(self, settings_page):
        super().__init__(title=gl.lm.get("deck.general-group.title"), description=gl.lm.get("deck.general-group.description"))
        self.set_margin_bottom(30)
        self.settings_page = settings_page
        self.deck_serial_number = settings_page.deck_serial_number

        self.build()

        self.load_defaults()
        self.connect("map", self.load_defaults)

    def build(self):
        self.name_row = Adw.EntryRow(title=gl.lm.get("deck.general-group.name"), show_apply_button=True)
        self.add(self.name_row)

    def load_defaults(self, *args):
        better_disconnect(self.name_row, self.on_name_applied)

        self.name_row.set_text(self.get_current_name())

        self.name_row.connect("apply", self.on_name_applied)

    def get_current_name(self) -> str:
        attributes = self.get_deck_stack().get_page_attributes(self.settings_page.deck_controller)
        if attributes is None:
            return ""
        return attributes[1]

    def get_deck_stack(self):
        return self.settings_page.deck_stack_child.deck_stack

    def on_name_applied(self, entry: Adw.EntryRow, *args):
        name = entry.get_text().strip()

        deck_settings = gl.settings_manager.get_deck_settings(self.deck_serial_number)
        if name == "":
            # Fall back to the name of the deck model
            deck_settings.pop("name", None)
        else:
            deck_settings["name"] = name
        gl.settings_manager.save_deck_settings(self.deck_serial_number, deck_settings)

        new_name = self.get_deck_stack().refresh_deck_name(self.settings_page.deck_controller)
        if new_name is not None and new_name != entry.get_text():
            entry.set_text(new_name)
