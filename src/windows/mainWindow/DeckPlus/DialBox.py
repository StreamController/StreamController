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

class DialBox(Gtk.Box):
    def __init__(self, page_settings_page: "PageSettingsPage", **kwargs):
        super().__init__(**kwargs)
        self.set_hexpand(True)
        self.set_homogeneous(True)
        self.page_settings_page = page_settings_page
        self.build()

    def build(self):
        for i in range(4):
            dial = Dial(self)
            self.append(dial)


class Dial(Gtk.Frame):
    def __init__(self, dial_box: DialBox, **kwargs):
        self.dial_box = dial_box
        super().__init__(**kwargs)
        self.set_halign(Gtk.Align.CENTER)
        self.set_css_classes(["dial-frame", "dial-frame-hidden"])
        self.set_overflow(Gtk.Overflow.HIDDEN)

        self.pixbuf = None

        self.image = Gtk.Image(css_classes=["dial"])
        self.image.set_overflow(Gtk.Overflow.HIDDEN)
        self.set_child(self.image)

        self.focus_controller = Gtk.EventControllerFocus()
        self.image.add_controller(self.focus_controller)
        self.focus_controller.connect("enter", self.on_focus_in)

        self.click_ctrl = Gtk.GestureClick().new()
        self.click_ctrl.connect("pressed", self.on_click)
        self.click_ctrl.set_button(0)
        self.image.add_controller(self.click_ctrl)
    
        # Make image focusable
        self.set_focus_child(self.image)
        self.image.set_focusable(True)

    def on_click(self, gesture, n_press, x, y):
        if gesture.get_current_button() == 1 and n_press == 1:
            # Single left click
            # Select key
            self.image.grab_focus()

        elif gesture.get_current_button() == 1 and n_press == 2:
            pass
            # Double left click
            # Simulate key press
            # self.simulate_press()

    def on_focus_in(self, *args):
        self.set_border_active(True)

    def set_border_active(self, active: bool):
        if active:
            if self.dial_box.page_settings_page.deck_config.active_widget not in [self, None]:
                self.dial_box.page_settings_page.deck_config.active_widget.set_border_active(False)
            self.dial_box.page_settings_page.deck_config.active_widget = self
            self.set_css_classes(["key-button-frame"])
        else:
            self.set_css_classes(["key-button-frame-hidden"])
            self.dial_box.page_settings_page.deck_config.active_widget = None