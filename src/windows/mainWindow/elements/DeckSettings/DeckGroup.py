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
# Import python modules
import os
import gi

from GtkHelper.GtkHelper import better_disconnect
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, GLib, Gdk, GObject

# Import Python modules
import cv2
import threading
from loguru import logger as log
from math import floor
from time import sleep
from typing import List
from PIL import Image

# Import globals
import globals as gl

# Import own modules
from src.backend.DeckManagement.ImageHelpers import image2pixbuf, is_transparent

class MediaListBox(Gtk.ListBox):
    # Custom signal for selection changes
    __gsignals__ = {
        'selection-changed': (GObject.SignalFlags.RUN_FIRST, None, ()),
    }
    
    def __init__(self, **kwargs):
        super().__init__(selection_mode=Gtk.SelectionMode.NONE, css_classes=["boxed-list"], **kwargs)
        
        # Load custom CSS
        css_provider = Gtk.CssProvider()
        css_provider.load_from_path("data/screensaver_media_list.css")
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(),
            css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )
        
        # Drag selection state
        self.drag_selecting = False
        self.drag_start_x = 0
        self.drag_start_y = 0
        self.drag_end_x = 0
        self.drag_end_y = 0
        self.selection_rect = None
        self.selected_rows = set()
        
        # Add gesture controller for drag selection
        self.drag_gesture = Gtk.GestureDrag()
        self.drag_gesture.connect("drag-begin", self.on_drag_begin)
        self.drag_gesture.connect("drag-update", self.on_drag_update)
        self.drag_gesture.connect("drag-end", self.on_drag_end)
        self.add_controller(self.drag_gesture)
        
        # Add click controller for individual selection
        self.click_gesture = Gtk.GestureClick()
        self.click_gesture.connect("pressed", self.on_pressed)
        self.add_controller(self.click_gesture)
        
        # Key controller for keyboard shortcuts
        self.key_controller = Gtk.EventControllerKey()
        self.key_controller.connect("key-pressed", self.on_key_pressed)
        self.add_controller(self.key_controller)
        
        # Store reference to the parent screensaver instance
        self.screensaver_instance = None
    
    def set_screensaver_instance(self, screensaver_instance):
        self.screensaver_instance = screensaver_instance
        
        # Create overlay for selection rectangle
        self.overlay = Gtk.Overlay()
        self.selection_drawing_area = Gtk.DrawingArea()
        self.selection_drawing_area.set_visible(False)
        
        # Use GTK4 snapshot approach for drawing
        self.selection_drawing_area.set_draw_func(self.on_selection_draw)
        
        # Reparent the listbox to be inside the overlay
        parent = self.get_parent()
        if parent:
            parent.remove(self)
        self.overlay.set_child(self)
        self.overlay.add_overlay(self.selection_drawing_area)
    
    def on_drag_begin(self, gesture, start_x, start_y):
        self.drag_selecting = True
        self.drag_start_x = start_x
        self.drag_start_y = start_y
        self.drag_end_x = start_x
        self.drag_end_y = start_y
        
        # Clear previous selection if not holding Ctrl
        if not (gesture.get_current_event_state() & Gdk.ModifierType.CONTROL_MASK):
            self.clear_selection()
        
        # Show selection rectangle
        self.selection_drawing_area.set_visible(True)
        self.selection_drawing_area.queue_draw()
    
    def on_drag_update(self, gesture, offset_x, offset_y):
        if not self.drag_selecting:
            return
            
        self.drag_end_x = self.drag_start_x + offset_x
        self.drag_end_y = self.drag_start_y + offset_y
        
        # Update selection
        self.update_selection_from_rect()
        
        # Redraw selection rectangle
        self.selection_drawing_area.queue_draw()
    
    def on_drag_end(self, gesture, offset_x, offset_y):
        if not self.drag_selecting:
            return
            
        self.drag_end_x = self.drag_start_x + offset_x
        self.drag_end_y = self.drag_start_y + offset_y
        
        # Final selection update
        self.update_selection_from_rect()
        
        # Hide selection rectangle
        self.selection_drawing_area.set_visible(False)
        self.drag_selecting = False
    
    def on_selection_draw(self, drawing_area, cr, width, height, user_data=None):
        if not self.drag_selecting:
            return
            
        # Calculate rectangle bounds
        x = min(self.drag_start_x, self.drag_end_x)
        y = min(self.drag_start_y, self.drag_end_y)
        rect_width = abs(self.drag_end_x - self.drag_start_x)
        rect_height = abs(self.drag_end_y - self.drag_start_y)
        
        # Draw selection rectangle
        cr.set_source_rgba(0.2, 0.6, 1.0, 0.3)  # Light blue fill
        cr.rectangle(x, y, rect_width, rect_height)
        cr.fill()
        
        cr.set_source_rgba(0.2, 0.6, 1.0, 0.8)  # Darker blue border
        cr.set_line_width(2)
        cr.rectangle(x, y, rect_width, rect_height)
        cr.stroke()
        
        return True
    
    def update_selection_from_rect(self):
        # Calculate rectangle bounds
        x = min(self.drag_start_x, self.drag_end_x)
        y = min(self.drag_start_y, self.drag_end_y)
        width = abs(self.drag_end_x - self.drag_start_x)
        height = abs(self.drag_end_y - self.drag_start_y)
        
        # Check each row if it intersects with the selection rectangle
        row = self.get_first_child()
        while row:
            if self.row_intersects_rect(row, x, y, width, height):
                self.select_row(row, add=True)
            else:
                # Only deselect if not holding Ctrl
                if not (self.drag_gesture.get_current_event_state() & Gdk.ModifierType.CONTROL_MASK):
                    self.deselect_row(row)
            row = row.get_next_sibling()
    
    def row_intersects_rect(self, row, rect_x, rect_y, rect_width, rect_height):
        # Get row bounds
        allocation = row.get_allocation()
        row_x = allocation.x
        row_y = allocation.y
        row_width = allocation.width
        row_height = allocation.height
        
        # Check intersection using basic geometry
        return not (row_x + row_width < rect_x or 
                   rect_x + rect_width < row_x or 
                   row_y + row_height < rect_y or 
                   rect_y + rect_height < row_y)
    
    def on_pressed(self, gesture, n_press, x, y):
        if n_press == 1 and not self.drag_selecting:
            # Find which row was clicked
            row = self.get_row_at_y(y)
            if row:
                # Toggle selection if Ctrl is pressed, otherwise select only this row
                if gesture.get_current_event_state() & Gdk.ModifierType.CONTROL_MASK:
                    if row in self.selected_rows:
                        self.deselect_row(row)
                    else:
                        self.select_row(row, add=True)
                else:
                    self.clear_selection()
                    self.select_row(row)
    
    def on_key_pressed(self, controller, keyval, keycode, state):
        if keyval == Gdk.KEY_Delete or keyval == Gdk.KEY_BackSpace:
            self.remove_selected_rows()
            return True
        elif keyval == Gdk.KEY_a and state & Gdk.ModifierType.CONTROL_MASK:
            self.select_all()
            return True
        elif keyval == Gdk.KEY_Escape:
            self.clear_selection()
            return True
        return False
    
    def select_row(self, row, add=False):
        if not add:
            self.clear_selection()
        
        if row not in self.selected_rows:
            self.selected_rows.add(row)
            row.add_css_class("selected")
            self.emit_selected_rows_changed()
    
    def deselect_row(self, row):
        if row in self.selected_rows:
            self.selected_rows.discard(row)
            row.remove_css_class("selected")
            self.emit_selected_rows_changed()
    
    def clear_selection(self):
        for row in list(self.selected_rows):
            self.deselect_row(row)
    
    def emit_selected_rows_changed(self):
        self.emit("selection-changed")
    
    def select_all(self):
        row = self.get_first_child()
        while row:
            self.select_row(row, add=True)
            row = row.get_next_sibling()
    
    def get_selected_rows(self):
        return list(self.selected_rows)
    
    def get_selected_media_paths(self):
        paths = []
        for row in self.selected_rows:
            if hasattr(row, 'media_path'):
                paths.append(row.media_path)
        return paths
    
    def get_row_at_y(self, y):
        # Find which row is at the given y coordinate
        row = self.get_first_child()
        while row:
            allocation = row.get_allocation()
            if allocation.y <= y <= allocation.y + allocation.height:
                return row
            row = row.get_next_sibling()
        return None
    
    def remove_selected_rows(self):
        if not self.screensaver_instance:
            return
            
        selected_paths = self.get_selected_media_paths()
        for path in selected_paths:
            # Find and remove each selected row
            row = self.get_first_child()
            while row:
                if hasattr(row, 'media_path') and row.media_path == path:
                    self.screensaver_instance.remove_media_item(path, row)
                    break
                row = row.get_next_sibling()
        
        self.clear_selection()


class DeckGroup(Adw.PreferencesGroup):
    def __init__(self, settings_page):
        super().__init__(title=gl.lm.get("deck.deck-group.title"), description=gl.lm.get("deck.deck-group.description"))
        self.deck_serial_number = settings_page.deck_serial_number

        self.brightness = Brightness(settings_page, self.deck_serial_number)
        self.screensaver = Screensaver(settings_page, self.deck_serial_number)
        self.rotation = Rotation(settings_page, self.deck_serial_number)

        self.add(self.brightness)
        self.add(self.screensaver)
        self.add(self.rotation)


class Rotation(Adw.PreferencesRow):
    def __init__(self, settings_page: "PageSettings", deck_serial_number, **kwargs):
        super().__init__()
        self.settings_page = settings_page
        self.deck_serial_number = deck_serial_number
        self.build()

        self.load_default()
        self.connect("map", self.load_default)

    def build(self):
        self.main_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, hexpand=True,
                                margin_start=15, margin_end=15, margin_top=15, margin_bottom=15)
        self.set_child(self.main_box)

        self.rotation_label = Gtk.Label(label=gl.lm.get("deck.deck-group.rotation"), hexpand=True, xalign=0)
        self.main_box.append(self.rotation_label)

        self.toggle_group = Adw.ToggleGroup()
        self.main_box.append(self.toggle_group)

        self.toggle_0 = Adw.Toggle(label="0°", name="0")
        self.toggle_group.add(self.toggle_0)

        self.toggle_90 = Adw.Toggle(label="90°", name="90")
        self.toggle_group.add(self.toggle_90)

        self.toggle_180 = Adw.Toggle(label="180°", name="180")
        self.toggle_group.add(self.toggle_180)

        self.toggle_270 = Adw.Toggle(label="270°", name="270")
        self.toggle_group.add(self.toggle_270)


        self.toggle_group.connect("notify::active", self.on_value_changed)

    def on_value_changed(self, _, __):
        GLib.idle_add(self.on_value_changed_idle)

    def on_value_changed_idle(self):
        rot = int(self.toggle_group.get_active_name())

        deck_settings = gl.settings_manager.get_deck_settings(self.deck_serial_number)
        deck_settings["rotation"] = rot
        gl.settings_manager.save_deck_settings(self.deck_serial_number, deck_settings)

        self.settings_page.deck_controller.set_rotation(rot)

    def load_default(self, *args):
        better_disconnect(self.toggle_group, "notify::active")

        rot = gl.settings_manager.get_deck_settings(self.deck_serial_number).get("rotation", 0)
        self.toggle_group.set_active_name(str(rot))

        self.toggle_group.connect("notify::active", self.on_value_changed)


class Brightness(Adw.PreferencesRow):
    def __init__(self, settings_page: "PageSettings", deck_serial_number, **kwargs):
        super().__init__()
        self.settings_page = settings_page
        self.deck_serial_number = deck_serial_number
        self.build()

        """
        To save performance and memory, we only load the thumbnail when the user sees the row
        """
        self.on_map_tasks: list = []
        self.connect("map", self.on_map)

        self.load_default()
        self.scale.connect("value-changed", self.on_value_changed)

    def on_map(self, widget):
        for f in self.on_map_tasks:
            f()
        self.on_map_tasks.clear()

    def build(self):
        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, hexpand=True,
                                margin_start=15, margin_end=15, margin_top=15, margin_bottom=15)
        self.set_child(self.main_box)

        self.label = Gtk.Label(label=gl.lm.get("deck.deck-group.brightness"), hexpand=True, xalign=0)
        self.main_box.append(self.label)

        self.scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, min=0, max=100, step=1)
        self.scale.set_draw_value(True)
        self.main_box.append(self.scale)

    def on_value_changed(self, scale):
        GLib.idle_add(self.on_value_changed_idle, scale)

    def on_value_changed_idle(self, scale):
        value = round(scale.get_value())

        # Update and save brightness in deck settings
        settings_manager = gl.settings_manager
        deck_settings = settings_manager.get_deck_settings(self.deck_serial_number)
        deck_settings.setdefault("brightness", {})["value"] = value
        settings_manager.save_deck_settings(self.deck_serial_number, deck_settings)

        # Check if brightness is overwritten by the current page
        page_dict = self.settings_page.deck_controller.active_page.dict
        overwrite = page_dict.get("settings", {}).get("brightness", {}).get("overwrite", False)

        # Apply brightness if not overwritten
        if not overwrite:
            self.settings_page.deck_controller.set_brightness(value)

    def load_default(self):
        if not self.get_mapped():
            self.on_map_tasks.clear()
            self.on_map_tasks.append(lambda: self.load_default())
            return
        
        original_values = gl.settings_manager.get_deck_settings(self.deck_serial_number)
        
        # Set defaut values 
        original_values.setdefault("brightness", {})
        brightness = original_values["brightness"].setdefault("value", 50)

        # Save if changed
        if original_values != gl.settings_manager.get_deck_settings(self.deck_serial_number):
            gl.settings_manager.save_deck_settings(self.deck_serial_number, original_values)

        # Update ui
        self.scale.set_value(brightness)


class Screensaver(Adw.PreferencesRow):
    def __init__(self, settings_page: "PageSettings", deck_serial_number, **kwargs):
        super().__init__()
        self.settings_page = settings_page
        self.deck_serial_number = deck_serial_number
        self.build()

        """
        To save performance and memory, we only load the thumbnail when the user sees the row
        """
        self.on_map_tasks: list = []
        self.connect("map", self.on_map)

        self.load_defaults()

    def on_map(self, widget):
        for f in self.on_map_tasks:
            f()
        self.on_map_tasks.clear()
    
    def build(self):
        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, hexpand=True,
                                margin_start=15, margin_end=15, margin_top=15, margin_bottom=15)
        self.set_child(self.main_box)

        self.enable_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, hexpand=True)
        self.main_box.append(self.enable_box)

        self.enable_label = Gtk.Label(label=gl.lm.get("deck.deck-group.enable-screensaver"), hexpand=True, xalign=0)
        self.enable_box.append(self.enable_label)

        self.enable_switch = Gtk.Switch()
        self.enable_box.append(self.enable_switch)

        self.config_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, hexpand=True, visible=False)
        self.main_box.append(self.config_box)

        self.config_box.append(Gtk.Separator(hexpand=True, margin_top=10, margin_bottom=10))

        self.time_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, hexpand=True)
        self.config_box.append(self.time_box)

        self.time_label = Gtk.Label(label=gl.lm.get("screensaver-delay"), hexpand=True, xalign=0)
        self.time_box.append(self.time_label)

        self.time_spinner = Gtk.SpinButton.new_with_range(1, 24*60, 1)
        self.time_box.append(self.time_spinner)

        self.media_selector_label = Gtk.Label(label=gl.lm.get("deck.deck-group.media-to-show"), hexpand=True, xalign=0)
        self.config_box.append(self.media_selector_label)

        self.media_mode_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, hexpand=True)
        self.config_box.append(self.media_mode_box)

        self.media_mode_label = Gtk.Label(label="Mode:", hexpand=True, xalign=0)
        self.media_mode_box.append(self.media_mode_label)

        self.media_mode_toggle = Adw.ToggleGroup()
        self.media_mode_box.append(self.media_mode_toggle)

        self.toggle_single = Adw.Toggle(label="Single", name="single")
        self.media_mode_toggle.add(self.toggle_single)

        self.toggle_multiple = Adw.Toggle(label="Multiple", name="multiple")
        self.media_mode_toggle.add(self.toggle_multiple)

        self.media_selector_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, halign=Gtk.Align.CENTER)
        self.config_box.append(self.media_selector_box)

        self.media_selector_button = Gtk.Button(label=gl.lm.get("deck.deck-group.media-select-label"), css_classes=["page-settings-media-selector"])
        self.media_selector_box.append(self.media_selector_button)

        self.media_list_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, hexpand=True, visible=False)
        self.config_box.append(self.media_list_box)

        self.media_list_label = Gtk.Label(label="Selected Media:", hexpand=True, xalign=0, margin_top=10)
        self.media_list_box.append(self.media_list_label)

        self.media_list_scrolled = Gtk.ScrolledWindow(min_content_height=150, max_content_height=200, vexpand=True)
        self.media_list_box.append(self.media_list_scrolled)

        self.media_list_container = MediaListBox()
        self.media_list_container.set_screensaver_instance(self)
        self.media_list_scrolled.set_child(self.media_list_container.overlay)

        # Add bulk action buttons
        bulk_actions_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5, margin_top=5, css_classes=["bulk-actions-box"])
        self.media_list_box.append(bulk_actions_box)

        self.remove_selected_button = Gtk.Button(label="Remove Selected", css_classes=["destructive-action"], sensitive=False)
        self.remove_selected_button.connect("clicked", self.on_remove_selected)
        bulk_actions_box.append(self.remove_selected_button)

        self.select_all_button = Gtk.Button(label="Select All", css_classes=["suggested-action"])
        self.select_all_button.connect("clicked", self.on_select_all)
        bulk_actions_box.append(self.select_all_button)

        self.clear_selection_button = Gtk.Button(label="Clear Selection")
        self.clear_selection_button.connect("clicked", self.on_clear_selection)
        bulk_actions_box.append(self.clear_selection_button)

        self.add_media_button = Gtk.Button(label="Add Media", css_classes=["suggested-action"])
        self.add_media_button.connect("clicked", self.on_add_media)
        bulk_actions_box.append(self.add_media_button)

        self.media_switch_interval_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, hexpand=True, visible=False)
        self.config_box.append(self.media_switch_interval_box)

        self.media_switch_interval_label = Gtk.Label(label="Switch Interval (minutes):", hexpand=True, xalign=0)
        self.media_switch_interval_box.append(self.media_switch_interval_label)

        self.media_switch_interval_spinner = Gtk.SpinButton.new_with_range(1, 60, 1)
        self.media_switch_interval_box.append(self.media_switch_interval_spinner)

        self.progress_bar = Gtk.ProgressBar(hexpand=True, margin_top=10, text=gl.lm.get("background.processing"), fraction=0, show_text=True, visible=False)
        self.config_box.append(self.progress_bar)

        self.media_selector_image = Gtk.Picture(overflow=Gtk.Overflow.HIDDEN, can_shrink=True) # Will be bound to the button by self.set_thumbnail()

        self.loop_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, hexpand=True, margin_bottom=15)
        self.config_box.append(self.loop_box)

        self.loop_label = Gtk.Label(label=gl.lm.get("deck.deck-group.media-loop"), hexpand=True, xalign=0)
        self.loop_box.append(self.loop_label)

        self.loop_switch = Gtk.Switch()
        self.loop_box.append(self.loop_switch)

        self.fps_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, hexpand=True)
        self.config_box.append(self.fps_box)

        self.fps_label = Gtk.Label(label=gl.lm.get("deck.deck-group.media-fps"), hexpand=True, xalign=0)
        self.fps_box.append(self.fps_label)

        self.fps_spinner = Gtk.SpinButton.new_with_range(1, 30, 1)
        self.fps_box.append(self.fps_spinner)

        self.brightness_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, hexpand=True)
        self.config_box.append(self.brightness_box)

        self.brightness_label = Gtk.Label(label=gl.lm.get("deck.deck-group.brightness"), hexpand=True, xalign=0)
        self.brightness_box.append(self.brightness_label)

        self.scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, min=0, max=100, step=1)
        self.brightness_box.append(self.scale)

        self.connect_signals()

    def connect_signals(self) -> None:
        self.enable_switch.connect("state-set", self.on_toggle_enable)
        self.time_spinner.connect("value-changed", self.on_change_time)
        self.media_selector_button.connect("clicked", self.on_choose_image)
        self.media_mode_toggle.connect("notify::active", self.on_media_mode_changed)
        self.media_switch_interval_spinner.connect("value-changed", self.on_change_media_switch_interval)
        self.loop_switch.connect("state-set", self.on_toggle_loop)
        self.fps_spinner.connect("value-changed", self.on_change_fps)
        self.scale.connect("value-changed", self.on_change_brightness)
        
        # Connect selection change signal
        self.media_list_container.connect("selection-changed", self.on_selection_changed)

    def disconnect_signals(self) -> None:
        self.enable_switch.disconnect_by_func(self.on_toggle_enable)
        self.time_spinner.disconnect_by_func(self.on_change_time)
        self.media_selector_button.disconnect_by_func(self.on_choose_image)
        self.media_mode_toggle.disconnect_by_func(self.on_media_mode_changed)
        self.media_switch_interval_spinner.disconnect_by_func(self.on_change_media_switch_interval)
        self.loop_switch.disconnect_by_func(self.on_toggle_loop)
        self.fps_spinner.disconnect_by_func(self.on_change_fps)
        self.scale.disconnect_by_func(self.on_change_brightness)
        
        # Disconnect selection change signal
        try:
            self.media_list_container.disconnect_by_func(self.on_selection_changed)
        except:
            pass

    def load_defaults(self):
        self.disconnect_signals()
        original_values = gl.settings_manager.get_deck_settings(self.deck_serial_number)
        
        # Set defaut values 
        original_values.setdefault("screensaver", {})
        enable = original_values["screensaver"].setdefault("enable", False)
        path = original_values["screensaver"].setdefault("media-path", None)
        media_paths = original_values["screensaver"].setdefault("media-paths", [])
        media_mode = original_values["screensaver"].setdefault("media-mode", "single")
        media_switch_interval = original_values["screensaver"].setdefault("media-switch-interval", 5)
        loop = original_values["screensaver"].setdefault("loop", False)
        fps = original_values["screensaver"].setdefault("fps", 30)
        time = original_values["screensaver"].setdefault("time-delay", 5)
        brightness = original_values["screensaver"].setdefault("brightness", 30)

        # Save if changed
        if original_values != gl.settings_manager.get_deck_settings(self.deck_serial_number):
            gl.settings_manager.save_deck_settings(self.deck_serial_number, original_values)

        # Update ui
        self.enable_switch.set_active(enable)
        self.config_box.set_visible(enable)
        self.time_spinner.set_value(time)
        self.media_mode_toggle.set_active_name(media_mode)
        self.media_switch_interval_spinner.set_value(media_switch_interval)
        self.loop_switch.set_active(loop)
        self.fps_spinner.set_value(fps)
        self.scale.set_value(brightness)

        # Update UI visibility based on mode
        self.on_media_mode_changed_ui_update(media_mode)

        # Load media paths
        self.load_media_paths(media_paths)

        if path is not None and media_mode == "single":
            if os.path.isfile(path):
                self.set_thumbnail(path)

        self.connect_signals()

    def on_toggle_enable(self, toggle_switch, state):
        config = gl.settings_manager.get_deck_settings(self.deck_serial_number)
        config.setdefault("screensaver", {})
        config["screensaver"]["enable"] = state
        # Save
        gl.settings_manager.save_deck_settings(self.deck_serial_number, config)
        # Update enable if not overwritten by the active page
        active_page = self.settings_page.deck_controller.active_page
        page_settings = active_page.dict.get("settings", {})
        overwrite = page_settings.get("screensaver", {}).get("overwrite")
        if overwrite is None:
            # Fallback to root for compatibility
            overwrite = active_page.dict.get("screensaver", {}).get("overwrite", False)

        if not overwrite:
            self.settings_page.deck_controller.screen_saver.set_enable(state)

        self.config_box.set_visible(state)

    def on_toggle_loop(self, toggle_switch, state):
        config = gl.settings_manager.get_deck_settings(self.deck_serial_number)
        config.setdefault("screensaver", {})
        config["screensaver"]["loop"] = state
        # Save
        gl.settings_manager.save_deck_settings(self.deck_serial_number, config)

        # Update loop if not overwritten by the active page
        active_page = self.settings_page.deck_controller.active_page
        page_settings = active_page.dict.get("settings", {})
        overwrite = page_settings.get("screensaver", {}).get("overwrite")
        if overwrite is None:
            # Fallback to root for compatibility
            overwrite = active_page.dict.get("screensaver", {}).get("overwrite", False)

        if not overwrite:
            self.settings_page.deck_controller.screen_saver.set_loop(state)

    def on_change_fps(self, spinner):
        config = gl.settings_manager.get_deck_settings(self.deck_serial_number)
        config.setdefault("screensaver", {})
        config["screensaver"]["fps"] = spinner.get_value_as_int()
        # Save
        gl.settings_manager.save_deck_settings(self.deck_serial_number, config)
        # Update fps if not overwritten by the active page
        active_page = self.settings_page.deck_controller.active_page
        page_settings = active_page.dict.get("settings", {})
        overwrite = page_settings.get("screensaver", {}).get("overwrite")
        if overwrite is None:
            # Fallback to root for compatibility
            overwrite = active_page.dict.get("screensaver", {}).get("overwrite", False)

        if not overwrite:
            self.settings_page.deck_controller.screen_saver.set_fps(spinner.get_value_as_int())

    def on_change_time(self, spinner):
        config = gl.settings_manager.get_deck_settings(self.deck_serial_number)
        config.setdefault("screensaver", {})
        config["screensaver"]["time-delay"] = round(spinner.get_value_as_int())
        # Save
        gl.settings_manager.save_deck_settings(self.deck_serial_number, config)
        # Update time if not overwritten by the active page
        active_page = self.settings_page.deck_controller.active_page
        page_settings = active_page.dict.get("settings", {})
        overwrite = page_settings.get("screensaver", {}).get("overwrite")
        if overwrite is None:
            # Fallback to root for compatibility
            overwrite = active_page.dict.get("screensaver", {}).get("overwrite", False)

        if not overwrite:
            self.settings_page.deck_controller.screen_saver.set_time(round(spinner.get_value_as_int()))

    def on_change_brightness(self, scale):
        config = gl.settings_manager.get_deck_settings(self.deck_serial_number)
        config.setdefault("screensaver", {})
        config["screensaver"]["brightness"] = scale.get_value()
        # Save
        gl.settings_manager.save_deck_settings(self.deck_serial_number, config)
        # Apply brightness if not overwritten
        active_page = self.settings_page.deck_controller.active_page
        page_settings = active_page.dict.get("settings", {})
        overwrite = page_settings.get("screensaver", {}).get("overwrite")
        if overwrite is None:
            # Fallback to root for compatibility
            overwrite = active_page.dict.get("screensaver", {}).get("overwrite", False)

        if not overwrite:
            self.settings_page.deck_controller.screen_saver.set_brightness(scale.get_value())

    def set_thumbnail(self, file_path):
        if file_path == None:
            return
        if not os.path.isfile(file_path):
            return
        image = gl.media_manager.get_thumbnail(file_path)
        
        pixbuf = image2pixbuf(image)
        self.media_selector_image.set_pixbuf(pixbuf)
        self.media_selector_button.set_child(self.media_selector_image)

    def on_choose_image(self, button):
        settings = gl.settings_manager.get_deck_settings(self.deck_serial_number)
        settings.setdefault("screensaver", {})
        media_path = settings["screensaver"].get("media-path", None)

        gl.app.let_user_select_asset(default_path=media_path, callback_func=self.update_image)

    def update_image(self, image_path):
        self.set_thumbnail(image_path)
        settings = gl.settings_manager.get_deck_settings(self.deck_serial_number)
        settings.setdefault("screensaver", {})
        settings["screensaver"]["media-path"] = image_path
        gl.settings_manager.save_deck_settings(self.deck_serial_number, settings)

        deck_controller = self.settings_page.deck_controller
        deck_controller.load_screensaver(deck_controller.active_page)

    def on_media_mode_changed(self, toggle_group, param):
        mode = toggle_group.get_active_name()
        self.on_media_mode_changed_ui_update(mode)
        
        config = gl.settings_manager.get_deck_settings(self.deck_serial_number)
        config.setdefault("screensaver", {})
        config["screensaver"]["media-mode"] = mode
        
        # When switching to single mode, transfer first media path from multiple mode
        if mode == "single":
            media_paths = config["screensaver"].get("media-paths", [])
            if media_paths and not config["screensaver"].get("media-path"):
                # Set the first media path as the single media path
                config["screensaver"]["media-path"] = media_paths[0]
                # Update the UI to show the selected media
                self.set_thumbnail(media_paths[0])
        
        gl.settings_manager.save_deck_settings(self.deck_serial_number, config)

        deck_controller = self.settings_page.deck_controller
        deck_controller.load_screensaver(deck_controller.active_page)

    def on_media_mode_changed_ui_update(self, mode):
        if mode == "single":
            self.media_selector_box.set_visible(True)
            self.media_list_box.set_visible(False)
            self.media_switch_interval_box.set_visible(False)
        else:  # multiple
            self.media_selector_box.set_visible(False)
            self.media_list_box.set_visible(True)
            self.media_switch_interval_box.set_visible(True)

    def on_add_media(self, button):
        config = gl.settings_manager.get_deck_settings(self.deck_serial_number)
        config.setdefault("screensaver", {})
        media_paths = config["screensaver"].get("media-paths", [])
        default_path = media_paths[0] if media_paths else None
        gl.app.let_user_select_asset(default_path=default_path, callback_func=self.add_media_to_list)

    def add_media_to_list(self, media_path):
        config = gl.settings_manager.get_deck_settings(self.deck_serial_number)
        config.setdefault("screensaver", {})
        media_paths = config["screensaver"].setdefault("media-paths", [])
        
        if media_path not in media_paths:
            media_paths.append(media_path)
            config["screensaver"]["media-paths"] = media_paths
            gl.settings_manager.save_deck_settings(self.deck_serial_number, config)
            
            self.add_media_item_to_ui(media_path)
            
            deck_controller = self.settings_page.deck_controller
            deck_controller.load_screensaver(deck_controller.active_page)

    def add_media_item_to_ui(self, media_path):
        row = Adw.ActionRow()
        row.set_title(os.path.basename(media_path))
        row.set_subtitle(media_path)
        row.media_path = media_path  # Store path for selection
        
        # Add thumbnail
        image = Gtk.Image()
        try:
            thumbnail = gl.media_manager.get_thumbnail(media_path)
            pixbuf = image2pixbuf(thumbnail)
            image.set_from_pixbuf(pixbuf)
        except:
            pass
        
        row.add_prefix(image)
        
        # Add remove button
        remove_button = Gtk.Button(label="Remove", css_classes=["destructive-action"])
        remove_button.connect("clicked", lambda btn: self.remove_media_item(media_path, row))
        row.add_suffix(remove_button)
        
        self.media_list_container.append(row)

    def remove_media_item(self, media_path, row):
        config = gl.settings_manager.get_deck_settings(self.deck_serial_number)
        config.setdefault("screensaver", {})
        media_paths = config["screensaver"].get("media-paths", [])
        
        if media_path in media_paths:
            media_paths.remove(media_path)
            config["screensaver"]["media-paths"] = media_paths
            gl.settings_manager.save_deck_settings(self.deck_serial_number, config)
            
            self.media_list_container.remove(row)
            
            deck_controller = self.settings_page.deck_controller
            deck_controller.load_screensaver(deck_controller.active_page)

    def load_media_paths(self, media_paths):
        # Clear existing items
        child = self.media_list_container.get_first_child()
        while child:
            next_child = child.get_next_sibling()
            self.media_list_container.remove(child)
            child = next_child
        
        # Add media paths
        for media_path in media_paths:
            self.add_media_item_to_ui(media_path)

    def on_change_media_switch_interval(self, spinner):
        config = gl.settings_manager.get_deck_settings(self.deck_serial_number)
        config.setdefault("screensaver", {})
        config["screensaver"]["media-switch-interval"] = round(spinner.get_value_as_int())
        gl.settings_manager.save_deck_settings(self.deck_serial_number, config)
        
        deck_controller = self.settings_page.deck_controller
        deck_controller.screen_saver.set_media_switch_interval(round(spinner.get_value_as_int()))

    def on_selection_changed(self, listbox):
        selected_count = len(listbox.get_selected_rows())
        self.remove_selected_button.set_sensitive(selected_count > 0)
        self.clear_selection_button.set_sensitive(selected_count > 0)

    def on_remove_selected(self, button):
        self.media_list_container.remove_selected_rows()

    def on_select_all(self, button):
        self.media_list_container.select_all()

    def on_clear_selection(self, button):
        self.media_list_container.clear_selection()
