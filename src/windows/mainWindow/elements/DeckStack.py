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

# Import globals
import globals as gl

# Import own modules
from src.windows.mainWindow.elements.DeckStackChild import DeckStackChild
from src.backend.DeckManagement.HelperMethods import recursive_hasattr

# Import typing
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from src.windows.mainWindow.elements.leftArea import LeftArea
    from src.windows.mainWindow.mainWindow import MainWindow

class DeckStack(Gtk.Stack):
    """
    A deck with childs for each connected deck
    """
    def __init__(self, main_window: "MainWindow", left_area: "LeftArea", deck_manager, **kwargs):
        super().__init__(**kwargs)
        self.deck_manager = deck_manager
        self.main_window = main_window
        self.left_area = left_area

        self.deck_names = []
        self.deck_numbers = []

        self.deck_attributes: dict = {}

    def on_switch(self, widget, *args):
        # Update page selector
        self.main_window.sidebar.page_selector.update_selected()

        child: DeckStackChild = self.get_visible_child()
        if child.stack.get_visible_child_name() == "page-settings":
            self.main_window.split_view.set_collapsed(False)

        else:
            self.main_window.split_view.set_collapsed(True)

    def build(self):
        self.connect("notify::visible-child-name", self.on_switch)

    def add_pages(self):
        for deck_controller in self.deck_manager.deck_controller:
            self.add_page(deck_controller)

        if len(self.deck_manager.deck_controller) == 0:
            self.main_window.change_ui_to_no_connected_deck()

    def add_page(self, deck_controller):
        attr = self.get_page_attributes(deck_controller)
        if attr is None:
            return
        deck_number, deck_type = attr

        page = DeckStackChild(self, deck_controller)
        self.add_titled(page, deck_number, deck_type)

        page.page_settings.deck_config.grid.select_key(0, 0)

        self.main_window.change_ui_to_connected_deck()

        self.main_window.reload_sidebar()
            
    def get_page_attributes(self, deck_controller) -> tuple:
        if deck_controller in self.deck_attributes:
            return self.deck_attributes[deck_controller]
        
        deck_type = deck_controller.deck.deck_type()
        try:
            serial_number = deck_controller.deck.get_serial_number()
        except Exception as e:
            log.error(e)
            return
        self.deck_numbers.append(serial_number)
        deck_number = str(deck_controller.deck.get_serial_number())

        if deck_type not in self.deck_names:
            self.deck_names.append(deck_type)
            self.deck_attributes[deck_controller] = deck_number, deck_type
            return deck_number, deck_type
        # name already exists
        while deck_type in self.deck_names:
            if deck_type[-1].isdigit():
                deck_type = deck_type[:-1] + chr(ord(deck_type[-1]) + 1)
            else:
                deck_type = deck_type + " 2"

        self.deck_names.append(deck_type)

        self.deck_attributes[deck_controller] = deck_number, deck_type

        return deck_number, deck_type

    def remove_page(self, deck_controller) -> str:
        was_visible: bool = False
        for i, page in enumerate(self.get_pages()):
            if page.get_child().deck_controller == deck_controller:
                if self.get_visible_child() == page.get_child():
                    was_visible = True
                # Remove from deck_names
                self.deck_names.remove(page.get_title())
                # Remove page from stack
                self.remove(page.get_child())
                break

        if not was_visible:
            return
        
        # Reload righ area
        self.main_window.reload_sidebar()
            
        # Show message if no decks are connected
        if len(self.get_pages()) == 0:
            self.main_window.change_ui_to_no_connected_deck()
            return


        new_index = i - 1
        if new_index < 0:
            new_index = i + 1

        self.set_visible_child(self.get_pages()[new_index].get_child())

    def focus_controller(self, deck_controller) -> None:
        for page in self.get_pages():
            if page.get_child().deck_controller == deck_controller:
                self.set_visible_child(page.get_child())
                return
            
    def get_visible_child(self) -> DeckStackChild:
        return super().get_visible_child()