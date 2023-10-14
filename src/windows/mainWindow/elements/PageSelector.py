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
from gi.repository import Gtk, Adw, Gio, GObject

# Import Python modules
from loguru import logger as log

class PageSelector(Gtk.Box):
    def __init__(self, main_window, page_manager):
        self.main_window = main_window
        self.page_manager = page_manager
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL)
        self.build()

    def build(self):
        # Label
        self.label = Gtk.Label(label="Page:", margin_start=3, margin_end=7, css_classes=["bold"])
        self.append(self.label)

        # Right area
        self.right_area = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, css_classes=["linked"])
        self.append(self.right_area)

        # Dropdown
        pages = self.get_pages()
        self.drop_down = Gtk.DropDown.new_from_strings(pages)
        self.drop_down.set_tooltip_text("Select page for active deck")
        self.right_area.append(self.drop_down)

        # Settings button
        self.settings_button = Gtk.Button(icon_name="settings", tooltip_text="Open Page Manager")
        self.right_area.append(self.settings_button)

    def get_pages(self):
        pages = self.page_manager.get_pages(remove_extension=True)
        active_deck_serial_number = self.main_window.leftArea.deck_stack.get_visible_child_name()
        log.debug(f"Active deck serial number: {active_deck_serial_number}")
        active_deck_default_page = self.page_manager.get_default_page_for_deck(active_deck_serial_number, remove_extension=True)
        # Add suffix to default page
        for page in pages:
            if page == active_deck_default_page:
                pages[pages.index(page)] = page + " (default)"

        return pages