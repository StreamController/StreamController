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
        self.stack = Gtk.Stack(hexpand=True, vexpand=True)
        self.set_child(self.stack)

        self.page_settings = PageSettingsPage(self, self.deck_controller)
        self.deck_settings = DeckSettingsPage(self, self.deck_controller)

        self.stack.add_titled(self.page_settings, "page-settings", "Page Settings")
        self.stack.add_titled(self.deck_settings, "deck-settings", "Deck Settings")

        # Switch overlay button
        self.toggle_settings_button = Gtk.Button(icon_name="configure", css_classes=["circular"],
                                  halign=Gtk.Align.END, valign=Gtk.Align.END, margin_end=50, margin_bottom=50)
        self.toggle_settings_button.connect("clicked", self.on_toggle_settings_button_click)
        self.add_overlay(self.toggle_settings_button)

    def on_toggle_settings_button_click(self, button):
        if self.stack.get_visible_child_name() == "page-settings":
            self.stack.set_visible_child_name("deck-settings")
            self.toggle_settings_button.set_icon_name("view-paged")
            gl.app.main_win.sidebar_toggle_button.set_visible(False)
            gl.app.main_win.split_view.set_collapsed(True)

        else:
            self.stack.set_visible_child_name("page-settings")
            self.toggle_settings_button.set_icon_name("configure")
            gl.app.main_win.sidebar_toggle_button.set_visible(True)
            gl.app.main_win.split_view.set_collapsed(False)