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
from src.windows.mainWindow.elements.DeckSettings.DeckGroup import DeckGroup
from src.windows.mainWindow.elements.DeckSettings.BackgroundGroup import BackgroundGroup
from src.windows.mainWindow.elements.DeckSettings.FakeDeckGroup import FakeDeckGroup

# Import globals
import globals as gl

class DeckSettingsPage(Gtk.Box):
    def __init__(self, deck_stack_child, deck_controller, **kwargs):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, hexpand=True, vexpand=True,
                         margin_start=50, margin_end=50,
                         margin_top=50, margin_bottom=50, **kwargs)
        self.deck_stack_child = deck_stack_child
        self.deck_controller = deck_controller
        self.deck_serial_number = deck_controller.deck.get_serial_number()
        if self.deck_controller.active_page == None:
            # TODO: Fix: Error not showing up
            self.show_no_page_error()
            return
        self.build()

    def build(self):
        self.scrolled_window = Gtk.ScrolledWindow(hexpand=True, vexpand=True)
        self.append(self.scrolled_window)

        clamp = Adw.Clamp()
        self.scrolled_window.set_child(clamp)

        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, hexpand=True)
        clamp.set_child(main_box)
        
        self.settings_group = DeckGroup(self)
        main_box.append(self.settings_group)

        self.background_group = BackgroundGroup(self)
        main_box.append(self.background_group)

        self.fake_deck_group = FakeDeckGroup(self)
        main_box.append(self.fake_deck_group)

        ## Hide the fake deck group if own deck is not fake
        deck = self.deck_controller.deck
        fake = False
        if hasattr(deck, "is_fake"):
            fake = deck.is_fake

        self.fake_deck_group.set_visible(fake)



    def show_no_page_error(self):
        self.clear()
        self.error_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, halign=Gtk.Align.CENTER, valign=Gtk.Align.CENTER)
        self.append(self.error_box)

        self.error_label = Gtk.Label(label="No page selected for this deck")
        self.error_box.append(self.error_label)

        # TODO: Do this automatically on page change
        self.retry_button = Gtk.Button(label="Retry")
        self.retry_button.connect("clicked", self.on_retry_button_click)
        self.error_box.append(self.retry_button)

    def on_retry_button_click(self, button):
        if self.deck_controller.active_page == None:
            return
        
        self.clear()
        self.build()

    def clear(self):
        while self.get_first_child() is not None:
            self.remove(self.get_first_child())