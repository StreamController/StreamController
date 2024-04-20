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

from src.backend.DeckManagement.HelperMethods import recursive_hasattr

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Gtk, Adw, Gdk, GLib, Gio

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from src.windows.mainWindow.elements.PageSettingsPage import PageSettingsPage

class ScreenBar(Gtk.Frame):
    def __init__(self, page_settings_page: "PageSettingsPage", **kwargs):
        self.page_settings_page = page_settings_page
        super().__init__(**kwargs)
        self.set_css_classes(["key-button-frame-hidden"])

        self.pixbuf = None

        self.image = Gtk.Image(hexpand=True, vexpand=True, css_classes=["key-image", "plus-screenbar"])
        self.image.set_overflow(Gtk.Overflow.HIDDEN)
        self.set_child(self.image)

        focus_controller = Gtk.EventControllerFocus()
        self.add_controller(focus_controller)
        focus_controller.connect("enter", self.on_focus_in)
        focus_controller.connect("leave", self.on_focus_out)

    
        # Make image focusable
        self.set_focus_child(self.image)
        self.image.set_focusable(True)

    def on_focus_in(self, *args):
        self.set_css_classes(["key-button-frame"])

    def on_focus_out(self, *args):
        self.set_css_classes(["key-button-frame-hidden"])