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

# Import own modules
from src.windows.mainWindow.elements.PageSettings.PageSettings import PageSettings
from src.windows.mainWindow.elements.DeckSettings.DeckSettingsPage import DeckSettingsPage
from src.windows.mainWindow.elements.PageSettingsPage import PageSettingsPage

# Import globals
import globals as gl

class DeckStackChild(Gtk.Overlay):
    """
    Child of DeckStack
    This stack features one page for the page specific settings and one for the deck settings
    """
    def __init__(self, deck_stack, deck_controller, **kwargs):
        super().__init__(**kwargs)
        self.deck_stack = deck_stack
        self.deck_controller = deck_controller

        self.build()

    def build(self):
        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, hexpand=True, vexpand=True)
        self.set_child(self.main_box)

        self.stack = Gtk.Stack(hexpand=True, vexpand=True)
        self.main_box.append(self.stack)

        self.page_settings = PageSettingsPage(self, self.deck_controller)
        self.deck_settings = DeckSettingsPage(self, self.deck_controller)

        self.stack.add_titled(self.page_settings, "page-settings", "Page Settings")
        self.stack.add_titled(self.deck_settings, "deck-settings", "Deck Settings")

        # Low-fps banner
        self.low_fps_banner = Adw.Banner(
            title=gl.lm.get("warning.low-fps"),
            button_label=gl.lm.get("warning.dismiss"),
            revealed=False
        )
        self.low_fps_banner.connect("button-clicked", self.on_banner_dismiss)
        self.main_box.prepend(self.low_fps_banner)

    def on_banner_dismiss(self, banner):
        banner.set_revealed(False)