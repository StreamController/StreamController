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
from src.windows.mainWindow.elements.DeckConfig import DeckConfig
from src.windows.mainWindow.elements.PageSettings.PageSettings import PageSettings

# Import globals
import globals as gl

# Import typing
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from src.windows.mainWindow.elements.DeckStack import DeckStackChild

class PageSettingsPage(Gtk.Overlay):
    """
    Child of DeckStackChild
    This stack features one page for the key grid and one for the page settings
    """
    def __init__(self, deck_stack_child: "DeckStackChild", deck_controller, **kwargs):
        self.deck_controller = deck_controller
        self.deck_stack_child = deck_stack_child
        super().__init__(hexpand=True, vexpand=True)
        self.build()

    def build(self):
        self.global_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, hexpand=True)
        self.set_child(self.global_box)

        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, hexpand=True)
        # self.set_child(self.main_box)
        self.global_box.append(self.main_box)


        # Add stack
        self.stack = Gtk.Stack(hexpand=True, vexpand=True)
        self.main_box.append(self.stack)

        # Add switcher
        self.switcher_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, hexpand=True)
        self.main_box.append(self.switcher_box)
        self.switcher = Switcher(self)
        self.switcher_box.append(self.switcher)
        
        ## Add stack pages
        self.deck_config = DeckConfig(self)
        self.stack.add_titled(self.deck_config, "deck-config", gl.lm.get("main-page-deck-config"))

        # Add settings
        self.settings_page = PageSettings(self)
        self.stack.add_titled(self.settings_page, "settings", gl.lm.get("main-page-page-settings"))

        # # Switch overlay button
        # self.open_deck_settings_button = Gtk.Button(icon_name="configure", css_classes=["circular"],
        #                               halign=Gtk.Align.END, valign=Gtk.Align.END, margin_end=20, margin_bottom=50)
        # self.open_deck_settings_button.connect("clicked", self.on_open_deck_settings_button_click)
        # self.add_overlay(self.open_deck_settings_button)
        return

        ## Page selector bar - just for testing
        self.page_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, vexpand=True, css_classes=["sidebar-color"])
        self.global_box.append(self.page_box)

        for i in range(5):
            self.icon = Gtk.Image(icon_name="insert-image", hexpand=False, halign=Gtk.Align.CENTER,
                                margin_bottom=15, pixel_size=30)
            self.page_box.append(self.icon)

        self.expand_button = Gtk.ToggleButton(icon_name="draw-arrow-back", css_classes=["flat"],
                                              valign=Gtk.Align.END, vexpand=True, margin_bottom=5)
        self.page_box.append(self.expand_button)

        

    def on_open_deck_settings_button_click(self, button):
        self.deck_stack_child.set_visible_child_name("deck-settings")
        gl.app.main_win.split_view.set_collapsed(True)
        gl.app.main_win.sidebar_toggle_button.set_visible(False)


class Switcher(Gtk.StackSwitcher):
    def __init__(self, deck_page, **kwargs):
        super().__init__(stack=deck_page.stack, **kwargs)
        self.deck_page = deck_page
        self.set_hexpand(True)
        self.set_margin_start(10)
        self.set_margin_end(10)
        self.build()

    def build(self):
        pass