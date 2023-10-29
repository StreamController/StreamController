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

class DeckSettingsPage(Gtk.Box):
    def __init__(self, deck_stack_child, deck_controller, **kwargs):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, hexpand=True, vexpand=True,
                         margin_start=50, margin_end=50,
                         margin_top=50, margin_bottom=50, **kwargs)
        self.deck_stack_child = deck_stack_child
        self.deck_controller = deck_controller
        self.deck_serial_number = deck_controller.deck.get_serial_number()
        self.build()

    def build(self):
        self.scrolled_window = Gtk.ScrolledWindow(hexpand=True, vexpand=True)
        self.append(self.scrolled_window)

        clamp = Adw.Clamp()
        self.scrolled_window.set_child(clamp)

        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, hexpand=True)
        clamp.set_child(main_box)
        
        settings_group = DeckGroup(self)
        main_box.append(settings_group)

        background_group = BackgroundGroup(self)
        main_box.append(background_group)