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

# Import own modules
from src.windows.mainWindow.elements.DeckStack import DeckStack
from GtkHelper.GtkHelper import ErrorPage

class LeftArea(Gtk.Stack):
    def __init__(self, main_window, deck_manager, **kwargs):
        super().__init__(**kwargs)
        self.deck_manager = deck_manager
        self.main_window = main_window
        self.build()

    def build(self):
        self.error_page = ErrorPage()
        self.error_page.set_error_text("No Decks Available")
        self.add_titled(self.error_page, "error", "Error")

        self.deck_stack = DeckStack(self.main_window, self, self.deck_manager)
        self.add_titled(self.deck_stack, "deck_stack", "Deck Stack")
        # Needs access to deck stack because it runs show_no_decks_error
        self.deck_stack.add_pages()
        self.deck_stack.build()

    def show_no_decks_error(self):
        print("show")
        self.set_visible_child(self.error_page)

    def hide_no_decks_error(self):
        print("hide")
        self.set_visible_child(self.deck_stack)

        print(self.get_visible_child_name())