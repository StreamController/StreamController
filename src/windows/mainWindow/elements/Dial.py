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

        unit = self.scroll_ctrl.get_unit()
        self.scroll_ctrl.connect("scroll", self.on_scroll)
        self.image.add_controller(self.scroll_ctrl)

        self.key_ctrl = Gtk.EventControllerKey()
        self.key_ctrl.connect("key-pressed", self.on_key)
        self.image.add_controller(self.key_ctrl)

        # self.image.connect("scroll", self.on_scroll_event)

        # Gdk.ScrollDirection.UP
    
        # Make image focusable
        self.set_focus_child(self.image)
        self.image.set_focusable(True)

        self.last_scroll = None


        ## Actions
        self.action_group = Gio.SimpleActionGroup()
        self.insert_action_group("dial", self.action_group)

        self.remove_action = Gio.SimpleAction.new("remove", None)
        self.remove_action.connect("activate", self.on_remove)
        self.action_group.add_action(self.remove_action)

        ## Shortcuts
        self.shortcut_controller = Gtk.ShortcutController()
        self.add_controller(self.shortcut_controller)

        remove_shortcut_action = Gtk.CallbackAction.new(self.on_remove)

        self.remove_shortcut = Gtk.Shortcut.new(Gtk.ShortcutTrigger.parse_string("Delete"), remove_shortcut_action)
        self.shortcut_controller.add_shortcut(self.remove_shortcut)



    def on_key(self, controller, keyval, keycode, state):
        return

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

        value = -1 if dy > 0 else 1

        controller = gl.app.main_win.get_active_controller()
        if controller is not None:
            controller.event_callback(self.identifier, DialEventType.TURN, value)

        self.last_scroll = time.time()

    def on_click(self, gesture, n_press, x, y):
        if gesture.get_current_button() == 1 and n_press == 1:
            # Single left click
            # Select dial
            self.image.grab_focus()

            controller = gl.app.main_win.get_active_controller()
            dial = controller.get_input(self.identifier)

            state = dial.get_active_state().state

            gl.app.main_win.sidebar.load_for_dial(self.identifier, state)

            if self.dial_box.deck_controller.deck.is_touch():
                dial_image = dial.get_active_state().get_rendered_touch_image()
                gl.app.main_win.sidebar.key_editor.icon_selector.set_image(dial_image)

        elif gesture.get_current_button() == 1 and n_press == 2:
            # Double left click
            # Simulate key press
            controller = gl.app.main_win.get_active_controller()
            if controller is not None:
                controller.event_callback(self.identifier, DialEventType.PUSH, 1)
                # Release after 100ms
                GLib.timeout_add(100, controller.event_callback, self.identifier, DialEventType.PUSH, 0)
            pass

        else:
            pass

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

    def on_remove(self, *args) -> None:
        controller = gl.app.main_win.get_active_controller()
        if controller is None:
            return
        
        active_page = controller.active_page
        if active_page is None:
            return

        dial = controller.get_input(self.identifier)
        
        if str(dial.state) not in active_page.dict.get(self.identifier.input_type, {}).get(self.identifier.json_identifier, {}).get("states", {}):
            return
        
        del active_page.dict[self.identifier.input_type][self.identifier.json_identifier]["states"][str(dial.state)]
        active_page.save()
        active_page.load()

        active_page.reload_similar_pages(identifier=self.identifier, reload_self=True)

        # Reload ui
        gl.app.main_win.sidebar.load_for_identifier(self.identifier, dial.state)
