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
import time
import gi

from StreamDeck.Devices.StreamDeck import DialEventType, TouchscreenEventType

from src.backend.DeckManagement.InputIdentifier import Input
from src.backend.DeckManagement.HelperMethods import recursive_hasattr

import globals as gl

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Gtk, Adw, Gdk, GLib, Gio

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from src.windows.mainWindow.elements.PageSettingsPage import PageSettingsPage
    from src.backend.DeckManagement.DeckController import DeckController

class DialBox(Gtk.Box):
    def __init__(self, deck_controller: "DeckController", page_settings_page: "PageSettingsPage", **kwargs):
        super().__init__(**kwargs)
        self.deck_controller = deck_controller
        self.set_hexpand(True)
        self.set_homogeneous(True)
        self.page_settings_page = page_settings_page
        self.build()

    def build(self):
        for i in range(self.deck_controller.deck.dial_count()):
            dial = Dial(self, Input.Dial(str(i)))
            self.append(dial)


class Dial(Gtk.Frame):
    def __init__(self, dial_box: DialBox, identifier: Input.Dial, **kwargs):
        super().__init__(**kwargs)

        self.dial_box = dial_box
        self.identifier = identifier
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
        # self.click_ctrl.set_button(4)
        self.image.add_controller(self.click_ctrl)

        self.scroll_ctrl = Gtk.EventControllerScroll()
        self.scroll_ctrl.set_flags(Gtk.EventControllerScrollFlags.VERTICAL)

        print(self.scroll_ctrl.get_unit())
        unit = self.scroll_ctrl.get_unit()
        self.scroll_ctrl.connect("scroll", self.on_scroll)
        self.image.add_controller(self.scroll_ctrl)

        self.key_ctrl = Gtk.EventControllerKey()
        self.key_ctrl.connect("key-pressed", self.on_key)
        self.image.add_controller(self.key_ctrl)

        # self.image.connect("scroll", self.on_scroll_event)

        # Gdk.ScrollDirection.UP
        self.image
    
        # Make image focusable
        self.set_focus_child(self.image)
        self.image.set_focusable(True)

        self.last_scroll = None

    def on_key(self, controller, keyval, keycode, state):
        print(f"Key: {keyval}, {keycode}, {state}")

    def on_scroll(self, gesture, dx, dy):
        if self.last_scroll:
            if time.time() - self.last_scroll < 0.17:
                return
        # print(Gdk.ScrollUnit.WHEEL)
        # print(gesture.get_current_event())
        if gesture.get_unit() == Gdk.ScrollUnit.WHEEL:
            dx *= 10
            dy *= 10
        # print(f"Scroll: {dx}, {dy}")

        value = -1 if dy < 0 else 1

        controller = gl.app.main_win.get_active_controller()
        if controller is not None:
            controller.dial_change_callback(controller.deck, self.n, DialEventType.TURN, value)

        self.last_scroll = time.time()

    def on_click(self, gesture, n_press, x, y):
        if gesture.get_current_button() == 1 and n_press == 1:
            # Single left click
            # Select key
            self.image.grab_focus()

            controller = gl.app.main_win.get_active_controller()
            dial = controller.get_input(self.identifier)

            state = dial.get_active_state().state

            gl.app.main_win.sidebar.load_for_dial(self.identifier, state
                                                  )
        elif gesture.get_current_button() == 1 and n_press == 2:
            # print("Double click / activate")

            controller = gl.app.main_win.get_active_controller()
            if controller is not None:
                controller.dial_change_callback(controller.deck, self.n, DialEventType.PUSH, 1)
                threading.Timer(0.2, lambda: controller.dial_change_callback(controller.deck, self.n, DialEventType.PUSH, 0)).start()
            pass
            # Double left click
            # Simulate key press
            # self.simulate_press()

        else:
            print(f"Other click: {gesture.get_current_button()}, {n_press}")

    def on_focus_in(self, *args):
        self.set_border_active(True)

    def set_border_active(self, active: bool):
        if active:
            if self.dial_box.page_settings_page.deck_config.active_widget not in [self, None]:
                self.dial_box.page_settings_page.deck_config.active_widget.set_border_active(False)
            self.dial_box.page_settings_page.deck_config.active_widget = self
            self.set_css_classes(["dial-frame", "dial-frame-visible"])
        else:
            self.set_css_classes(["dial-frame", "dial-frame-hidden"])
            self.dial_box.page_settings_page.deck_config.active_widget = None