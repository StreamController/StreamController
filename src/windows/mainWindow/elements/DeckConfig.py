"""
Author: Core447
Year: 2024

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
any later version.

This programm comes with ABSOLUTELY NO WARRANTY!

You should have received a copy of the GNU General Public License
along with this program. If not, see <https://www.gnu.org/licenses/>.
"""
# Import gtk modules
import threading
import gi

from src.backend.DeckManagement.InputIdentifier import Input

import globals as gl

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw

# Import own modules
from src.windows.mainWindow.elements.KeyGrid import KeyGrid
from src.windows.mainWindow.DeckPlus.ScreenBar import ScreenBar
from src.windows.mainWindow.DeckPlus.DialBox import DialBox
from src.windows.mainWindow.DeckNeo.ScreenBar import ScreenBar as NeoScreenBar

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from src.windows.mainWindow.elements.PageSettingsPage import PageSettingsPage

class DeckConfig(Gtk.Box):
    def __init__(self, page_settings_page: "PageSettingsPage"):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, homogeneous=False,
                         halign=Gtk.Align.CENTER, valign=Gtk.Align.CENTER)
        self.page_settings_page = page_settings_page

        self.active_widget = None
        self.build()

    def build(self):
        # Add key grid
        self.grid = KeyGrid(self.page_settings_page.deck_controller, self.page_settings_page)
        self.append(self.grid)

        if self.page_settings_page.deck_controller.deck.is_touch():
            self.screenbar = ScreenBar(self.page_settings_page, Input.Touchscreen("sd-plus"))
            self.append(self.screenbar)
        elif self.page_settings_page.deck_controller.has_screen():
            self.screenbar = NeoScreenBar(self.page_settings_page, Input.Screen("sd-neo"))
            self.append(self.screenbar)

        if self.page_settings_page.deck_controller.deck.touch_key_count() > 0:
            self.touch_key_box = TouchKeyBox(self.page_settings_page)
            self.append(self.touch_key_box)

        self.dial_box = DialBox(self.page_settings_page.deck_controller, self.page_settings_page)
        self.append(self.dial_box)


class TouchKeyBox(Gtk.Box):
    def __init__(self, page_settings_page: "PageSettingsPage", **kwargs):
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL, halign=Gtk.Align.CENTER,
                         spacing=10, margin_top=5, margin_bottom=5, **kwargs)
        self.page_settings_page = page_settings_page
        deck_controller = page_settings_page.deck_controller

        for i in range(deck_controller.deck.touch_key_count()):
            label = "◀" if i == 0 else "▶"
            btn = TouchKeyButton(page_settings_page, i, label)
            self.append(btn)


class TouchKeyButton(Gtk.Button):
    def __init__(self, page_settings_page: "PageSettingsPage", index: int, label: str, **kwargs):
        super().__init__(label=label, css_classes=["flat"], width_request=60, height_request=40, **kwargs)
        self.page_settings_page = page_settings_page
        self.index = index
        self.connect("clicked", self.on_clicked)

    def on_clicked(self, button):
        self.set_border_active(True)
        identifier = Input.TouchKey(str(self.index))
        controller_input = self.page_settings_page.deck_controller.get_input(identifier)
        if controller_input is None:
            return
        state = controller_input.get_active_state().state
        gl.app.main_win.sidebar.load_for_identifier(identifier, state)

    def set_border_active(self, active: bool):
        deck_config = self.page_settings_page.deck_config
        if active:
            if deck_config.active_widget not in [self, None]:
                deck_config.active_widget.set_border_active(False)
            deck_config.active_widget = self
            self.add_css_class("suggested-action")
            self.remove_css_class("flat")
        else:
            self.remove_css_class("suggested-action")
            self.add_css_class("flat")
            deck_config.active_widget = None