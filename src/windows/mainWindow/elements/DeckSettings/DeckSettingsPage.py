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

from GtkHelper.GtkHelper import BackButton
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

class DeckSettingsPage(Gtk.Overlay):
    def __init__(self, deck_stack_child, deck_controller, **kwargs):
        super().__init__(hexpand=True, vexpand=True,
                         margin_start=50, margin_end=50,
                         margin_top=0, margin_bottom=50, **kwargs)
        self.deck_stack_child = deck_stack_child
        self.deck_controller = deck_controller
        self.deck_serial_number = deck_controller.deck.get_serial_number()
        self.build()
        if self.deck_controller.active_page == None:
            # TODO: Fix: Error not showing up
            self.show_no_page_error()
            return

    def build(self):
        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, hexpand=True)
        self.set_child(self.main_box)

        ## Back button
        self.back_button = BackButton(halign=Gtk.Align.START)
        self.back_button.connect("clicked", self.on_back_clicked)
        self.main_box.append(self.back_button)

        ## Main area
        self.scrolled_window = Gtk.ScrolledWindow(hexpand=True, vexpand=True, margin_top=50)
        self.main_box.append(self.scrolled_window)

        self.clamp = Adw.Clamp()
        self.scrolled_window.set_child(self.clamp)

        self.clamp_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, hexpand=True)
        self.clamp.set_child(self.clamp_box)
        
        self.settings_group = DeckGroup(self)
        self.clamp_box.append(self.settings_group)

        self.background_group = BackgroundGroup(self)
        self.clamp_box.append(self.background_group)

        self.fake_deck_group = FakeDeckGroup(self)
        self.clamp_box.append(self.fake_deck_group)
        self.fake_deck_group.set_visible(False) # Not stable enough to be shown #FIXME

        ## Hide the fake deck group if own deck is not fake
        deck = self.deck_controller.deck
        fake = False
        if hasattr(deck, "is_fake"):
            fake = deck.is_fake

        self.fake_deck_group.set_visible(fake)

        self.serial_number_label = Gtk.Label(label=f"Serial: {self.deck_controller.serial_number()}", margin_top=20, margin_bottom=20, css_classes=["dim-label"], selectable=True)
        self.main_box.append(self.serial_number_label)

    def on_back_clicked(self, button):
        self.deck_stack_child.stack.set_visible_child_name("page-settings")
        self.deck_stack_child.toggle_settings_button.set_icon_name("applications-system-symbolic")
        

    def on_open_page_settings_button_click(self, button):
        self.deck_stack_child.set_visible_child_name("page-settings")



    def show_no_page_error(self):
        self.clear()
        self.error_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, halign=Gtk.Align.CENTER, valign=Gtk.Align.CENTER)
        self.main_box.append(self.error_box)

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
        while self.main_box.get_first_child() is not None:
            self.main_box.remove(self.main_box.get_first_child())