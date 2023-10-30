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
from gi.repository import Gtk, Adw, Gdk

# Import Python modules
from loguru import logger as log

class ActionEditor(Gtk.Box):
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

class ActionGroup(Adw.PreferencesGroup):
    def __init__(self, right_area, **kwargs):
        super().__init__(title="Actions", description="Actions for this key", **kwargs)
        self.right_area = right_area

        self.active_coords = None

        self.actions = []

        self.build()

    def build(self):
        self.add_action("Name 1", "Category")
        self.add_action("Name 2", "Category")
        self.add_action("Name 3", "Category")
        self.add_action("Name 4", "Category")
        self.add_action("Name 5", "Category")
        self.add_action("Name 6", "Category")

    def add_action(self, action_name, action_category):
        action_row = ActionRow(action_name, action_category, self.right_area, len(self.actions))
        self.actions.append(action_row)
        self.add(action_row)

    def reorder_child_after(self, child, after):
        # return
        child_index = self.get_index_of_child(child)
        after_index = self.get_index_of_child(after)

        if child_index == None or after_index == None:
            log.warning("Child or after index is None")

        self.remove(child)
        self.actions.pop(child_index)
        self.actions.insert(after_index, child)

        old_actions = self.actions

        # Remove actions
        for i in range(len(self.actions)):
            self.remove(self.actions[i])
        self.actions = []

        # Add actions
        for i in range(len(old_actions)):
            self.add(old_actions[i])
            self.actions.append(old_actions[i])

    def get_index_of_child(self, child):
        for i in range(len(self.actions)):
            if self.actions[i] == child:
                return i
            
    def add_drop_preview(self, index):
        if hasattr(self, "preview"):
            if self.preview != None:
                self.reorder_child_after(self.preview, self.actions[index])
                return


        self.preview = ActionRow("Preview", "Preview", self.right_area, None)
        self.preview.set_sensitive(False)
        
        old_actions = self.actions
        old_actions.insert(index, self.preview)

        # Remove actions
        for i in range(len(self.actions)):
            self.remove(self.actions[i])
        self.actions = []

        # Add actions
        for i in range(len(old_actions)):
            self.add(old_actions[i])
            self.actions.append(old_actions[i])


class ActionRow(Adw.PreferencesRow):
    def __init__(self, action_name, action_category, right_area, index, **kwargs):
        super().__init__(**kwargs)
        self.action_name = action_name
        self.action_category = action_category
        self.right_area = right_area
        self.index = index
        self.active_coords = None
        self.build()
        self.init_dnd()

    def build(self):
        self.main_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, hexpand=True, margin_start=15, margin_end=15, margin_top=15, margin_bottom=15)
        self.set_child(self.main_box)

        self.left_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, hexpand=True)
        self.main_box.append(self.left_box)

        self.name_label = Gtk.Label(label=self.action_name, xalign=0, css_classes=["bold"])
        self.left_box.append(self.name_label)

        self.category_label = Gtk.Label(label=self.action_category, xalign=0, sensitive=False)
        self.left_box.append(self.category_label)

        # self.remove_button = Gtk.Button(label="Remove Action")
        # self.left_box.append(self.remove_button)

        self.main_box.append(Gtk.Image(icon_name="draw-arrow-forward"))\
        
    def init_dnd(self):
        if self.index == None:
            return
        # DnD Source
        dnd_source = Gtk.DragSource()
        dnd_source.set_actions(Gdk.DragAction.COPY)
        dnd_source.connect("prepare", self.on_dnd_prepare)
        dnd_source.connect("drag-begin", self.on_dnd_begin)
        dnd_source.connect("drag-end", self.on_dnd_end)

        self.add_controller(dnd_source)

        # DnD Target
        dnd_target = Gtk.DropTarget.new(self, Gdk.DragAction.COPY)
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
        if isinstance(value, ActionRow):
            self.right_area.action_editor.action_group.reorder_child_after(value, self)
            # Remove preview
            index = self.right_area.action_editor.action_group.get_index_of_child(self.right_area.action_editor.action_group.preview)
            self.right_area.action_editor.action_group.remove(self.right_area.action_editor.action_group.preview)
            self.right_area.action_editor.action_group.actions.pop(index)
        return True
    
    def on_dnd_motion(self, drop_target, x, y):
        # print(f"{drop_target}, {x}, {y}")
        self.right_area.action_editor.action_group.add_drop_preview(self.index)

