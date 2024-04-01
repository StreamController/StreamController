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

        # Switch overlay button
        self.toggle_settings_button = Gtk.Button(icon_name="applications-system-symbolic", css_classes=["circular"],
                                  halign=Gtk.Align.END, valign=Gtk.Align.END, margin_end=50, margin_bottom=50)
        self.toggle_settings_button.connect("clicked", self.on_toggle_settings_button_click)
        self.add_overlay(self.toggle_settings_button)

        # Low-fps banner
        self.low_fps_banner = Adw.Banner(
            title=gl.lm.get("warning.low-fps"),
            button_label=gl.lm.get("warning.dismiss"),
            revealed=False
        )
        self.low_fps_banner.connect("button-clicked", self.on_banner_dismiss)
        self.main_box.prepend(self.low_fps_banner)

    def on_toggle_settings_button_click(self, button):
        if self.stack.get_visible_child_name() == "page-settings":
            self.stack.set_visible_child_name("deck-settings")
            self.toggle_settings_button.set_icon_name("view-paged-symbolic")
            gl.app.main_win.sidebar_toggle_button.set_visible(False)
            gl.app.main_win.split_view.set_collapsed(True)

        else:
            self.stack.set_visible_child_name("page-settings")
            self.toggle_settings_button.set_icon_name("applications-system-symbolic")
            gl.app.main_win.sidebar_toggle_button.set_visible(True)
            gl.app.main_win.split_view.set_collapsed(False)

    def on_banner_dismiss(self, banner):
        banner.set_revealed(False)