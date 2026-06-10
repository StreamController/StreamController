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
import math
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

        self.dials: list[Dial] = []
        self.build()


    def build(self):
        for i in range(self.deck_controller.deck.dial_count()):
            dial = Dial(self, Input.Dial(str(i)))
            self.dials.append(dial)
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
        self.click_ctrl.set_button(0)
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
        
        # Software knob properties
        self.knob_rotation = 0  # Current rotation angle in degrees
        self.knob_dragging = False
        self.knob_last_angle = 0
        self.knob_start_y = 0
        self.knob_sensitivity = 2.0  # Degrees per pixel of vertical drag
        
        # Add drag controller for software knob
        self.drag_controller = Gtk.GestureDrag()
        self.drag_controller.connect("drag-begin", self.on_knob_drag_begin)
        self.drag_controller.connect("drag-update", self.on_knob_drag_update)
        self.drag_controller.connect("drag-end", self.on_knob_drag_end)
        self.image.add_controller(self.drag_controller)
        
        # Set cursor for drag interaction
        self.image.set_cursor(Gdk.Cursor.new_from_name("grab"))


        ## Actions
        self.action_group = Gio.SimpleActionGroup()
        self.insert_action_group("dial", self.action_group)

        self.turn_left_action = Gio.SimpleAction.new("turn-left", None)
        self.turn_right_action = Gio.SimpleAction.new("turn-right", None)
        self.copy_action = Gio.SimpleAction.new("copy", None)
        self.cut_action = Gio.SimpleAction.new("cut", None)
        self.paste_action = Gio.SimpleAction.new("paste", None)
        self.remove_action = Gio.SimpleAction.new("remove", None)
        self.update_action = Gio.SimpleAction.new("update", None)

        self.turn_left_action.connect("activate", self.on_turn_left)
        self.turn_right_action.connect("activate", self.on_turn_right)
        self.copy_action.connect("activate", self.on_copy)
        self.cut_action.connect("activate", self.on_cut)
        self.paste_action.connect("activate", self.on_paste)
        self.remove_action.connect("activate", self.on_remove)
        self.update_action.connect("activate", self.on_update)

        self.action_group.add_action(self.turn_left_action)
        self.action_group.add_action(self.turn_right_action)
        self.action_group.add_action(self.copy_action)
        self.action_group.add_action(self.cut_action)
        self.action_group.add_action(self.paste_action)
        self.action_group.add_action(self.remove_action)
        self.action_group.add_action(self.update_action)

        ## Shortcuts
        self.shortcut_controller = Gtk.ShortcutController()
        self.add_controller(self.shortcut_controller)

        turn_left_shortcut_action = Gtk.CallbackAction.new(self.on_turn_left)
        turn_right_shortcut_action = Gtk.CallbackAction.new(self.on_turn_right)
        copy_shortcut_action = Gtk.CallbackAction.new(self.on_copy)
        cut_shortcut_action = Gtk.CallbackAction.new(self.on_cut)
        paste_shortcut_action = Gtk.CallbackAction.new(self.on_paste)
        remove_shortcut_action = Gtk.CallbackAction.new(self.on_remove)
        update_shortcut_action = Gtk.CallbackAction.new(self.on_update)

        self.turn_left_shortcut = Gtk.Shortcut.new(Gtk.ShortcutTrigger.parse_string("Left"), turn_left_shortcut_action)
        self.turn_right_shortcut = Gtk.Shortcut.new(Gtk.ShortcutTrigger.parse_string("Right"), turn_right_shortcut_action)
        self.copy_shortcut = Gtk.Shortcut.new(Gtk.ShortcutTrigger.parse_string("<Primary>c"), copy_shortcut_action)
        self.cut_shortcut = Gtk.Shortcut.new(Gtk.ShortcutTrigger.parse_string("<Primary>x"), cut_shortcut_action)
        self.paste_shortcut = Gtk.Shortcut.new(Gtk.ShortcutTrigger.parse_string("<Primary>v"), paste_shortcut_action)
        self.remove_shortcut = Gtk.Shortcut.new(Gtk.ShortcutTrigger.parse_string("Delete"), remove_shortcut_action)
        self.update_shortcut = Gtk.Shortcut.new(Gtk.ShortcutTrigger.parse_string("F5"), update_shortcut_action)

        self.shortcut_controller.add_shortcut(self.turn_left_shortcut)
        self.shortcut_controller.add_shortcut(self.turn_right_shortcut)
        self.shortcut_controller.add_shortcut(self.copy_shortcut)
        self.shortcut_controller.add_shortcut(self.cut_shortcut)
        self.shortcut_controller.add_shortcut(self.paste_shortcut)
        self.shortcut_controller.add_shortcut(self.remove_shortcut)
        self.shortcut_controller.add_shortcut(self.update_shortcut)



    def on_key(self, controller, keyval, keycode, state):
        # Handle arrow keys for software knob turning when dial is focused
        if keyval == Gdk.KEY_Left:
            self.on_turn_left()
            return True
        elif keyval == Gdk.KEY_Right:
            self.on_turn_right()
            return True
        return False

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

        elif gesture.get_current_button() == 3 and n_press == 1:
            # Single right click
            # Open context menu
            popover = DialContextMenu(self)
            popover.popup()

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

    def on_knob_drag_begin(self, gesture, start_x, start_y):
        """Initialize drag state when user starts dragging the knob"""
        self.knob_dragging = True
        self.knob_start_y = start_y
        # Calculate initial angle based on drag position relative to center
        widget_size = min(self.get_width(), self.get_height())
        if widget_size > 0:
            center_x = widget_size / 2
            center_y = widget_size / 2
            self.knob_last_angle = math.degrees(math.atan2(start_y - center_y, start_x - center_x))
        else:
            self.knob_last_angle = 0
        
        # Change cursor to grabbing
        self.image.set_cursor(Gdk.Cursor.new_from_name("grabbing"))

    def on_knob_drag_update(self, gesture, offset_x, offset_y):
        """Handle drag updates to turn the knob"""
        if not self.knob_dragging:
            return
            
        # Get the start point correctly for GTK4
        start_point = gesture.get_start_point()
        start_x = start_point.x
        start_y = start_point.y
        current_x = start_x + offset_x
        current_y = start_y + offset_y
        
        # Calculate angle based on current position relative to center
        widget_size = min(self.get_width(), self.get_height())
        if widget_size > 0:
            center_x = widget_size / 2
            center_y = widget_size / 2
            current_angle = math.degrees(math.atan2(current_y - center_y, current_x - center_x))
            
            # Calculate angle difference
            angle_diff = current_angle - self.knob_last_angle
            
            # Handle angle wrap-around
            if angle_diff > 180:
                angle_diff -= 360
            elif angle_diff < -180:
                angle_diff += 360
            
            # Update rotation
            self.knob_rotation += angle_diff
            self.knob_rotation = self.knob_rotation % 360  # Keep within 0-360
            
            # Trigger dial turn events based on rotation
            if abs(angle_diff) > 5:  # Threshold to prevent too many events
                steps = int(abs(angle_diff) / 10)  # One step per 10 degrees
                direction = 1 if angle_diff > 0 else -1
                
                for _ in range(steps):
                    self.on_turn_right() if direction > 0 else self.on_turn_left()
                
                self.knob_last_angle = current_angle

    def on_knob_drag_end(self, gesture, offset_x, offset_y):
        """Clean up drag state when user stops dragging"""
        self.knob_dragging = False
        # Reset cursor to grab
        self.image.set_cursor(Gdk.Cursor.new_from_name("grab"))

    def on_turn_left(self, *args):
        """Turn the knob one step to the left in software"""
        controller = gl.app.main_win.get_active_controller()
        if controller is not None:
            controller.event_callback(self.identifier, DialEventType.TURN, -1)

    def on_turn_right(self, *args):
        """Turn the knob one step to the right in software"""
        controller = gl.app.main_win.get_active_controller()
        if controller is not None:
            controller.event_callback(self.identifier, DialEventType.TURN, 1)

    def on_copy(self, *args):
        controller = gl.app.main_win.get_active_controller()
        if controller is None:
            return
        
        active_page = controller.active_page
        if active_page is None:
            return
        
        dial_dict = active_page.dict.get(self.identifier.input_type, {}).get(self.identifier.json_identifier, {})
        gl.app.main_win.key_dict = dial_dict
        content = Gdk.ContentProvider.new_for_value(dial_dict)
        gl.app.main_win.key_clipboard.set_content(content)

    def on_cut(self, *args):
        self.on_copy()
        self.on_remove()

    def on_paste(self, *args):
        # Check if clipboard is from this StreamController
        if not gl.app.main_win.key_clipboard.is_local() and False:  # TODO: Rely on system keyboard - Enabling this will cause copy/paste problems on KDE/Wayland
            #TODO: Use read_value_async to read it instead - This is more like a temporary hack
            return
        
        # Remove the old action objects - useful in case the same action base is used across multiple actions because we would have no way to differentiate them
        self.on_remove()
        
        controller = gl.app.main_win.get_active_controller()
        if controller is None:
            return
        
        active_page = controller.active_page
        if active_page is None:
            return
        
        active_page.dict.setdefault(self.identifier.input_type, {})
        active_page.dict[self.identifier.input_type].setdefault(self.identifier.json_identifier, {})
        active_page.dict[self.identifier.input_type][self.identifier.json_identifier] = gl.app.main_win.key_dict
        active_page.reload_similar_pages(identifier=self.identifier, reload_self=True)

        # Reload ui
        dial = controller.get_input(self.identifier)
        if dial is not None:
            gl.app.main_win.sidebar.load_for_identifier(self.identifier, dial.state)

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

    def on_update(self, *args, **kwargs):
        controller = gl.app.main_win.get_active_controller()
        if controller is None:
            return
        
        dial = controller.get_input(self.identifier)
        if dial is None:
            return
            
        # Reload the dial's current state
        dial.update()


class DialContextMenu(Gtk.PopoverMenu):
    def __init__(self, dial: Dial, **kwargs):
        super().__init__(**kwargs)
        self.dial = dial
        self.build()

        self.connect("closed", self.on_close)

    def build(self):
        self.set_has_arrow(False)

        self.main_menu = Gio.Menu.new()

        self.copy_paste_menu = Gio.Menu.new()
        self.remove_menu = Gio.Menu.new()

        # Add actions to menus
        self.copy_paste_menu.append("Copy", "dial.copy")
        self.copy_paste_menu.append("Cut", "dial.cut")
        self.copy_paste_menu.append("Paste", "dial.paste")
        self.remove_menu.append("Remove", "dial.remove")
        self.remove_menu.append("Update", "dial.update")

        # Add sections to menu
        self.main_menu.append_section(None, self.copy_paste_menu)
        self.main_menu.append_section(None, self.remove_menu)

        self.set_menu_model(self.main_menu)

    def popup(self):
        """Override popup to set parent just before showing"""
        if self.dial and not self.get_parent():
            self.set_parent(self.dial)
        super().popup()

    def on_close(self, *args, **kwargs):
        return
    
    def on_open(self, *args, **kwargs):
        return