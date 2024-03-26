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
import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw

# Import own modules
from src.windows.Settings.Settings import Settings

# Import Python modules
from loguru import logger as log

# Import globals
import globals as gl

class NoDecksError(Gtk.Box):
    """
    This error gets shown if there are no decks registered/available
    """
    def __init__(self):
        super().__init__(
            orientation=Gtk.Orientation.VERTICAL,
            halign=Gtk.Align.CENTER,
            valign=Gtk.Align.CENTER,
            homogeneous=False,
            hexpand=True, vexpand=True
        )

        self.build()

    def build(self):
        self.no_pages_label = Gtk.Label(label=gl.lm.get("errors.no-deck.header"), css_classes=["error-label"])
        self.append(self.no_pages_label)

        self.add_button = Gtk.Button(label=gl.lm.get("errors.no-deck.add-fake"), margin_top=60, css_classes=["error-resolve-button"],
                                            hexpand=False, margin_start=60, margin_end=60, halign=Gtk.Align.CENTER)
        self.add_button.connect("clicked", self.on_add_click)
        self.append(self.add_button)

    def on_add_click(self, button):
        self.settings = Settings()
        self.settings.set_visible_page(self.settings.dev_page)
        self.settings.present()