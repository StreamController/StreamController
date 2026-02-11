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
from gi.repository import Gtk, Adw, GLib, Gdk, GObject

# Import python modules
from fuzzywuzzy import fuzz
import threading
from loguru import logger as log
from typing import List

# Import globals
import globals as gl

# Import own modules
from src.backend.DeckManagement.HelperMethods import is_video
from src.windows.AssetManager.CustomAssets.AssetPreview import AssetPreview

# Import typing
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from src.windows.AssetManager.CustomAssets.Chooser import CustomAssetChooser


class CustomAssetChooserFlowBox(Gtk.Box):
    # Custom signal for selection changes
    __gsignals__ = {
        'selection-changed': (GObject.SignalFlags.RUN_FIRST, None, ()),
    }
    
    def __init__(self, asset_chooser, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.set_orientation(Gtk.Orientation.HORIZONTAL)
        self.set_hexpand(True)

        self.asset_chooser:"CustomAssetChooser" = asset_chooser

        self.all_assets:list["AssetPreview"] = []
        
        # Drag selection state
        self.drag_selecting = False
        self.drag_start_x = 0
        self.drag_start_y = 0
        self.drag_end_x = 0
        self.drag_end_y = 0
        self.selected_children = set()
        self.selected_children_order = []  # Track order of selection
        self.selection_overlay = None
        self.selection_drawing_area = None
        
        # Load custom CSS
        css_provider = Gtk.CssProvider()
        css_provider.load_from_path("data/asset_manager_drag_select.css")
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(),
            css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

        self.build()

        self.flow_box.set_filter_func(self.filter_func)
        self.flow_box.set_sort_func(self.sort_func)


    def build(self):
        # Create overlay for drag selection
        self.selection_overlay = Gtk.Overlay()
        self.selection_drawing_area = Gtk.DrawingArea()
        self.selection_drawing_area.set_visible(False)
        self.selection_drawing_area.set_draw_func(self.on_selection_draw)
        
        self.flow_box = Gtk.FlowBox(hexpand=True, orientation=Gtk.Orientation.HORIZONTAL)
        self.flow_box.connect("child-activated", self.on_child_activated)
        
        # Set up drag selection
        self.setup_drag_selection()
        
        # Add to overlay
        self.selection_overlay.set_child(self.flow_box)
        self.selection_overlay.add_overlay(self.selection_drawing_area)
        
        GLib.idle_add(self.append, self.selection_overlay)

        for asset in gl.asset_manager_backend.get_all():
            asset = AssetPreview(flow=self, asset=asset, width_request=100, height_request=100)
            GLib.idle_add(self.flow_box.append, asset)

    def setup_drag_selection(self):
        # Add gesture controller for drag selection to the overlay
        self.drag_gesture = Gtk.GestureDrag()
        self.drag_gesture.connect("drag-begin", self.on_drag_begin)
        self.drag_gesture.connect("drag-update", self.on_drag_update)
        self.drag_gesture.connect("drag-end", self.on_drag_end)
        self.selection_overlay.add_controller(self.drag_gesture)
        
        # Add click controller for individual selection to the overlay
        self.click_gesture = Gtk.GestureClick()
        self.click_gesture.connect("pressed", self.on_pressed)
        self.selection_overlay.add_controller(self.click_gesture)
        
        # Key controller for keyboard shortcuts
        self.key_controller = Gtk.EventControllerKey()
        self.key_controller.connect("key-pressed", self.on_key_pressed)
        self.selection_overlay.add_controller(self.key_controller)
    
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
        
        # Check each child if it intersects with the selection rectangle
        for child in self.flow_box:
            if self.child_intersects_rect(child, x, y, width, height):
                self.select_child(child, add=True)
            else:
                # Only deselect if not holding Ctrl
                if not (self.drag_gesture.get_current_event_state() & Gdk.ModifierType.CONTROL_MASK):
                    self.deselect_child(child)
    
    def child_intersects_rect(self, child, rect_x, rect_y, rect_width, rect_height):
        # Get child bounds
        allocation = child.get_allocation()
        child_x = allocation.x
        child_y = allocation.y
        child_width = allocation.width
        child_height = allocation.height
        
        # Check intersection using basic geometry
        return not (child_x + child_width < rect_x or 
                   rect_x + rect_width < child_x or 
                   child_y + child_height < rect_y or 
                   rect_y + rect_height < child_y)
    
    def on_pressed(self, gesture, n_press, x, y):
        if n_press == 1 and not self.drag_selecting:
            # Find which child was clicked
            child = self.flow_box.get_child_at_pos(x, y)
            if child:
                # Toggle selection if Ctrl is pressed, otherwise select only this child
                if gesture.get_current_event_state() & Gdk.ModifierType.CONTROL_MASK:
                    if child in self.selected_children:
                        self.deselect_child(child)
                    else:
                        self.select_child(child, add=True)
                else:
                    # If we have multiple selections and clicking a new item, keep the first selected item
                    if len(self.selected_children) > 1 and child not in self.selected_children:
                        # Get the first selected child (using order tracking)
                        first_child = self.selected_children_order[0] if self.selected_children_order else None
                        # Clear all selections except the first one
                        for selected_child in list(self.selected_children):
                            if selected_child != first_child:
                                self.deselect_child(selected_child)
                        # Select the new clicked child
                        self.select_child(child, add=True)
                    elif child in self.selected_children:
                        # Clicking on an already selected child - make it the only selection
                        # Keep this child, deselect all others
                        for selected_child in list(self.selected_children):
                            if selected_child != child:
                                self.deselect_child(selected_child)
                    else:
                        # Single selection mode - clear and select this child
                        self.clear_selection()
                        self.select_child(child)
    
    def on_key_pressed(self, controller, keyval, keycode, state):
        if keyval == Gdk.KEY_Delete or keyval == Gdk.KEY_BackSpace:
            self.delete_selected_assets()
            return True
        elif keyval == Gdk.KEY_a and state & Gdk.ModifierType.CONTROL_MASK:
            self.select_all()
            return True
        elif keyval == Gdk.KEY_Escape:
            self.clear_selection()
            return True
        return False
    
    def select_child(self, child, add=False):
        if not add:
            self.clear_selection()
        
        if child not in self.selected_children:
            self.selected_children.add(child)
            self.selected_children_order.append(child)  # Track order
            child.add_css_class("selected")
            self.emit_selection_changed()
    
    def deselect_child(self, child):
        if child in self.selected_children:
            self.selected_children.remove(child)
            self.selected_children_order.remove(child)  # Remove from order
            child.remove_css_class("selected")
            self.emit_selection_changed()
    
    def clear_selection(self):
        for child in list(self.selected_children):
            self.deselect_child(child)
    
    def select_all(self):
        for child in self.flow_box:
            self.select_child(child, add=True)
    
    def get_selected_children(self):
        return list(self.selected_children)
    
    def get_selected_assets(self):
        return [child.asset for child in self.selected_children]
    
    def get_selection_count(self):
        return len(self.selected_children)
    
    def emit_selection_changed(self):
        self.emit("selection-changed")
    
    def delete_selected_assets(self):
        selected_assets = self.get_selected_assets()
        for asset in selected_assets:
            try:
                gl.asset_manager_backend.remove_asset(asset["internal-path"])
            except Exception as e:
                log.error(f"Failed to delete asset {asset['internal-path']}: {e}")
        
        # Refresh the flow box
        self.refresh_assets()
        self.clear_selection()
    def refresh_assets(self):
        # Clear existing assets
        for child in list(self.flow_box):
            self.flow_box.remove(child)
        
        # Reload assets
        self.all_assets.clear()
        for asset in gl.asset_manager_backend.get_all():
            asset = AssetPreview(flow=self, asset=asset, width_request=100, height_request=100)
            GLib.idle_add(self.flow_box.append, asset)
    
    def show_for_path(self, path):
        i = 0
        while True:
            child = self.flow_box.get_child_at_index(i)
            if child == None:
                return
            if child.asset["internal-path"] == path:
                GLib.idle_add(self.flow_box.select_child, child)
                return
            i += 1
            
    def filter_func(self, child):
        search_string = self.asset_chooser.search_entry.get_text()
        show_image = self.asset_chooser.image_button.get_active()
        show_video = self.asset_chooser.video_button.get_active()

        child_is_video = is_video(child.asset["internal-path"])

        if child_is_video and not show_video:
            return False
        if not child_is_video and not show_image:
            return False
        
        if search_string == "":
            return True
        
        fuzz_score = fuzz.ratio(search_string.lower(), child.name.lower())
        if fuzz_score < 40:
            return False
        
        return True
    
    def sort_func(self, a, b):
        search_string = self.asset_chooser.search_entry.get_text()

        if search_string == "":
            # Sort alphabetically
            if a.asset["name"] < b.asset["name"]:
                return -1
            if a.asset["name"] > b.asset["name"]:
                return 1
            return 0
        
        a_fuzz = fuzz.ratio(search_string.lower(), a.asset["name"].lower())
        b_fuzz = fuzz.ratio(search_string.lower(), b.asset["name"].lower())

        if a_fuzz > b_fuzz:
            return -1
        elif a_fuzz < b_fuzz:
            return 1
        
        return 0
    
    def on_child_activated(self, flow_box, child):
        # Handle single selection - close immediately
        if len(self.selected_children) <= 1:
            if callable(self.asset_chooser.asset_manager.callback_func):
                callback_thread = threading.Thread(target=self.callback_thread, args=(), name="flow_box_callback_thread")
                callback_thread.start()
            self.asset_chooser.asset_manager.close()
        # For multiple selections, don't close - let auto-add handle it on window close

    @log.catch
    def callback_thread(self):
        # Get all selected children
        selected_children = self.get_selected_children()
        if selected_children:
            for child in selected_children:
                self.asset_chooser.asset_manager.callback_func(child.asset["internal-path"],
                                                        *self.asset_chooser.asset_manager.callback_args,
                                                        **self.asset_chooser.asset_manager.callback_kwargs)
