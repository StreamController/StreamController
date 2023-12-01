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
from gi.repository import Gtk, Adw, Gdk, GLib

# Import Python modules
from loguru import logger as log
from copy import copy
import asyncio
import threading

# Import globals
import globals as gl

# Import own modules
from src.backend.PluginManager.ActionBase import ActionBase
from src.GtkHelper import BetterExpander

class ActionManager(Gtk.Box):
    def __init__(self, right_area, **kwargs):
        self.right_area = right_area
        super().__init__(**kwargs)
        self.build()

    def build(self):
        self.clamp = Adw.Clamp()
        self.append(self.clamp)

        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, hexpand=True)
        self.clamp.set_child(self.main_box)

        self.action_group = ActionGroup(self.right_area)
        self.main_box.append(self.action_group)

    def load_for_coords(self, coords):
        self.action_group.load_for_coords(coords)

class ActionGroup(Adw.PreferencesGroup):
    def __init__(self, right_area, **kwargs):
        super().__init__(**kwargs)
        self.right_area = right_area

        self.active_coords = None

        self.actions = []

        self.build()

    def build(self):
        self.expander = ActionExpanderRow(self)
        self.add(self.expander)

    def load_for_coords(self, coords):
        self.expander.load_for_coords(coords)


class ActionExpanderRow(BetterExpander):
    def __init__(self, action_group):
        super().__init__(title="Actions", subtitle="Actions for this key")
        self.set_expanded(True)
        self.action_group = action_group
        self.active_coords = None

        self.preview = None

        self.build()

    def build(self):
        self.add_action_button = AddActionButtonRow(self)
        self.add_row(self.add_action_button)

    def add_action_row(self, action_name, action_category, action_object, index):
        action_row = ActionRow(action_name, action_category, action_object, self.action_group.right_area, index)
        self.add_row(action_row)

    def load_for_coords(self, coords):
        self.clear_actions(keep_add_button=True)
        self.active_coords = coords
        page_coords = f"{coords[0]}x{coords[1]}"
        controller = self.action_group.right_area.main_window.leftArea.deck_stack.get_visible_child().deck_controller
        if page_coords not in controller.active_page.action_objects:
            return
        for i, key in enumerate(controller.active_page.action_objects[page_coords]):
            action =  controller.active_page.action_objects[page_coords][key]
            if isinstance(action, ActionBase):
                self.add_action_row(action.ACTION_NAME, action.PLUGIN_BASE.PLUGIN_NAME, action, i)
            elif isinstance(action, str):
                # No plugin installed for this action
                missing_button_row = MissingActionButtonRow(action, page_coords, i)
                self.add_row(missing_button_row)

        # Place add button at the end
        if len(self.get_rows()) > 0:
            self.reorder_child_after(self.add_action_button, self.get_rows()[-1])

    def clear_actions(self, keep_add_button=False):
        self.clear()
        if keep_add_button:
            self.add_row(self.add_action_button)

    def get_index_of_child(self, child):
        for i, action in enumerate(self.actions):
            if action == child:
                return i
            
    def add_drop_preview(self, index):
        #TODO: Fix this function, it does not work
        # return
        if hasattr(self, "preview"):
            if self.preview != None:
                # self.reorder_child_after(self.preview, self.get_rows()[index])
                GLib.idle_add(self.reorder_child_after, self.preview, self.get_rows()[index])
                return


        self.preview = Adw.PreferencesRow(title="Preview", height_request=100)
        self.preview.set_sensitive(False)
        self.add_row(self.preview)

        self.reorder_child_after(self.preview, self.get_rows()[index])

class ActionRow(Adw.PreferencesRow):
    def __init__(self, action_name, action_category, action_object, right_area, index, **kwargs):
        super().__init__(**kwargs, css_classes=["no-padding"])
        self.action_name = action_name
        self.action_category = action_category
        self.right_area = right_area
        self.action_object = action_object
        self.index = index
        self.active_coords = None
        self.build()
        self.init_dnd()

    def build(self):
        self.button = Gtk.Button(hexpand=True, vexpand=True, overflow=Gtk.Overflow.HIDDEN, css_classes=["no-margin", "invisible"])
        self.button.connect("clicked", self.on_click)
        self.set_child(self.button)

        self.main_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, hexpand=True, margin_start=15, margin_end=15, margin_top=15, margin_bottom=15)
        self.button.set_child(self.main_box)

        self.left_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, hexpand=True)
        self.main_box.append(self.left_box)

        self.name_label = Gtk.Label(label=self.action_name, xalign=0, css_classes=["bold"])
        self.left_box.append(self.name_label)

        self.category_label = Gtk.Label(label=self.action_category, xalign=0, sensitive=False)
        self.left_box.append(self.category_label)

        # self.remove_button = Gtk.Button(label="Remove Action")
        # self.left_box.append(self.remove_button)

        self.main_box.append(Gtk.Image(icon_name="draw-arrow-forward"))
        
    def init_dnd(self):
        if self.index == None:
            return
        # DnD Source
        dnd_source = Gtk.DragSource()
        dnd_source.set_actions(Gdk.DragAction.MOVE)
        dnd_source.connect("prepare", self.on_dnd_prepare)
        dnd_source.connect("drag-begin", self.on_dnd_begin)
        dnd_source.connect("drag-end", self.on_dnd_end)

        self.add_controller(dnd_source)

        # DnD Target
        dnd_target = Gtk.DropTarget.new(self, Gdk.DragAction.MOVE)
        dnd_target.set_gtypes([ActionRow])
        dnd_target.connect("drop", self.on_dnd_drop)
        dnd_target.connect("motion", self.on_dnd_motion)

        self.add_controller(dnd_target)

    def on_dnd_begin(self, drag_source, data):
        content = data.get_content()

    def on_dnd_end(self, drag_source, data, flag):
        pass

    def on_dnd_prepare(self, drag_source, x, y):
        drag_source.set_icon(
            Gtk.WidgetPaintable.new(self),
            self.get_width() / 2, self.get_height() / 2
        )
        content = Gdk.ContentProvider.new_for_value(self)
        return content

    def on_dnd_drop(self, drop_target, value, x, y):
        if not isinstance(value, ActionRow):
            return False
        
        self.right_area.key_editor.action_editor.action_group.expander.reorder_child_after(value, self)
        return True
        # Remove preview
        index = self.right_area.key_editor.action_editor.action_group.expander.get_index_of_child(self.right_area.key_editor.action_editor.action_group.expander.preview)
        self.right_area.key_editor.action_editor.action_group.expander.remove(self.right_area.key_editor.action_editor.action_group.expander.preview)
        self.right_area.key_editor.action_editor.action_group.expander.actions.pop(index)
        return True
    
    def on_dnd_motion(self, drop_target, x, y):
        print(f"Motion: {x}, {y}")
        print(f"Shape: {self.get_height()}")

        if y > self.get_height() / 2:
            self.right_area.key_editor.action_editor.action_group.expander.add_drop_preview(self.index-1)
        else:
            self.right_area.key_editor.action_editor.action_group.expander.add_drop_preview(self.index)
        return Gdk.DragAction.MOVE


        self.right_area.key_editor.action_editor.action_group.expander.add_drop_preview(self.index)

        return Gdk.DragAction.MOVE

    def on_click(self, button):
        self.right_area.action_configurator.load_for_action(self.action_object, self.index)
        self.right_area.show_action_configurator()


class MissingActionButtonRow(Adw.PreferencesRow):
    def __init__(self, action_id:str, page_coords:str, index:int):
        super().__init__(css_classes=["no-padding"])
        self.action_id = action_id
        self.page_coords = page_coords
        self.index = index

        self.main_overlay = Gtk.Overlay()
        self.set_child(self.main_overlay)

        self.main_button = Gtk.Button(hexpand=True, css_classes=["invisible"])
        self.main_button.connect("clicked", self.on_click)
        self.main_overlay.set_child(self.main_button)

        self.main_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, hexpand=True,
                                margin_bottom=10, margin_top=10)
        self.main_button.set_child(self.main_box)

        # Counter part for the button on the right - other wise the label is not centered
        self.main_box.append(Gtk.Box(width_request=50))
    
        self.center_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, hexpand=True)
        self.main_box.append(self.center_box)

        self.spinner = Gtk.Spinner(spinning=False, margin_bottom=5, visible=False)
        self.center_box.append(self.spinner)

        self.label = Gtk.Label(label=f"Install Missing Plugin", xalign=Gtk.Align.CENTER, vexpand=True, valign=Gtk.Align.CENTER)
        self.center_box.append(self.label)

        self.button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, width_request=50)
        self.main_box.append(self.button_box)

        self.remove_button = Gtk.Button(icon_name="delete", vexpand=False, halign=Gtk.Align.END, css_classes=["red-background"], margin_end=0,
                                        tooltip_text="Remove this action") # alternative icon: edit-delete-remove
        self.remove_button.connect("clicked", self.on_remove_click)
        # self.button_box.append(self.remove_button)
        self.main_overlay.add_overlay(self.remove_button)

    def on_click(self, button):
        self.spinner.set_visible(True)
        self.spinner.start()
        self.label.set_text("Installing Missing Plugin")

        # Run in thread to allow the ui to update
        threading.Thread(target=self.install).start()

    def install(self):
        # Get missing plugin from id
        plugin = asyncio.run(gl.app.store.backend.get_plugin_for_id(self.action_id))
        # Install plugin
        success = asyncio.run(gl.app.store.backend.install_plugin(plugin))
        if success == 404:
            self.show_install_error()
            return

        # Reset ui
        self.spinner.set_visible(False)
        self.spinner.stop()
        self.label.set_text("Install Missing Plugin")

    def show_install_error(self):
        self.spinner.set_visible(False)
        self.spinner.stop()
        self.label.set_text("Install Failed")
        self.set_css_classes(["error"])
        self.set_sensitive(False)
        self.main_button.set_sensitive(False)

        # Hide error after 3s
        threading.Timer(3, self.hide_install_error).start()

    def hide_install_error(self):
        self.label.set_text("Install Missing Plugin")
        self.remove_css_class("error")
        self.set_sensitive(True)
        self.main_button.set_sensitive(True)

    def on_remove_click(self, button):
        controller = gl.app.main_win.leftArea.deck_stack.get_visible_child().deck_controller
        page = controller.active_page

        # Remove from action objects
        del page.action_objects[self.page_coords][self.index]

        # Remove from page json
        page["keys"][self.page_coords]["actions"].pop(self.index)
        page.save()

        # Reload configurator ui
        gl.app.main_win.rightArea.key_editor.action_editor.load_for_coords(self.page_coords.split("x"))


class AddActionButtonRow(Adw.PreferencesRow):
    def __init__(self, expander, **kwargs):
        super().__init__(**kwargs, css_classes=["no-padding", "add-button"])
        self.expander = expander

        self.button = Gtk.Button(hexpand=True, vexpand=True, overflow=Gtk.Overflow.HIDDEN,
                                 css_classes=["no-margin", "invisible"],
                                 label=gl.lm.get("action-editor-add-new-action"),
                                 margin_bottom=5, margin_top=5)
        self.button.connect("clicked", self.on_click)
        self.set_child(self.button)

    def on_click(self, button):
        self.expander.action_group.right_area.let_user_select_action(callback_function=self.add_action)

    def add_action(self, action_class):
        log.trace(f"Adding action: {action_class}")

        # Gather data
        action_string = gl.plugin_manager.get_action_string_from_action(action_class)
        active_controller = self.expander.action_group.right_area.main_window.leftArea.deck_stack.get_visible_child().deck_controller
        active_page = active_controller.active_page
        page_coords = f"{self.expander.active_coords[0]}x{self.expander.active_coords[1]}"

        # Set missing values
        active_page.setdefault("keys", {})
        active_page["keys"].setdefault(page_coords, {})
        active_page["keys"][page_coords].setdefault("actions", [])

        # Add action
        active_page["keys"][page_coords]["actions"].append({
            "name": action_string,
            "settings": {}
        })

        # Save page
        active_page.save()
        # Reload page to add an object to the new action
        active_page.load()

        # Reload ui
        self.expander.load_for_coords(self.expander.active_coords)

        # Reload key
        controller = self.expander.action_group.right_area.main_window.leftArea.deck_stack.get_visible_child().deck_controller
        controller.load_key(page_coords)