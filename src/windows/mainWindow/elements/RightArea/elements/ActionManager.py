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


class ActionExpanderRow(Adw.ExpanderRow):
    def __init__(self, action_group):
        super().__init__(title="Actions", subtitle="Actions for this key")
        self.set_expanded(True)
        self.actions = []
        self.action_group = action_group

        self.preview = None

        self.build()

    def build(self):
        self.add_action_row("Name 1", "Category")
        self.add_action_row("Name 2", "Category")
        self.add_action_row("Name 3", "Category")

        self.add_action_button = AddActionButtonRow(self)
        self.add_row(self.add_action_button)

    def add_action_row(self, action_name, action_category):
        action_row = ActionRow(action_name, action_category, self.action_group.right_area, len(self.actions))
        self.actions.append(action_row)
        self.add_row(action_row)

    def reorder_child_after(self, child, after):
        # self.remove(self.actions[0])
        # return
        # return

        child_index = self.get_index_of_child(child)
        after_index = self.get_index_of_child(after)

        if child_index == None or after_index == None:
            log.warning("Child or after index is None")
            return
        
        old_actions = self.actions

        # return

        # Remove all actions
        for action in self.actions:
            if type(action) != ActionRow:
                continue
            self.remove(action)

        # Change order in self.actions
        self.actions.pop(child_index)
        self.actions.insert(after_index, child)


        # Add actions in new order
        for i in range(len(self.actions)):
            self.add_row(self.actions[i])
            # self.actions.append(self.actions[i])

    def get_index_of_child(self, child):
        for i in range(len(self.actions)):
            if self.actions[i] == child:
                return i
            
    def add_drop_preview(self, index):
        #TODO: Fix this function, it does not work
        return
        if hasattr(self, "preview"):
            if self.preview != None:
                self.reorder_child_after(self.preview, self.actions[index])
                return


        self.preview = ActionRow("Preview", "Preview", self.action_group.right_area, None)
        self.preview.set_sensitive(False)
        self.actions.append(self.preview)

        # Remove actions
        for i in range(len(self.actions)):
            self.remove(self.actions[i])
        
        # old_actions = self.actions
        self.actions.insert(index, self.preview)

        # self.actions = []

        # Add actions
        for i in range(len(self.actions)):
            self.add_row(self.actions[i])
            # self.actions.append(old_actions[i])



class ActionRow(Adw.PreferencesRow):
    def __init__(self, action_name, action_category, right_area, index, **kwargs):
        super().__init__(**kwargs, css_classes=["no-padding"])
        self.action_name = action_name
        self.action_category = action_category
        self.right_area = right_area
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
        # Remove preview
        index = self.right_area.key_editor.action_editor.action_group.expander.get_index_of_child(self.right_area.key_editor.action_editor.action_group.expander.preview)
        self.right_area.key_editor.action_editor.action_group.expander.remove(self.right_area.key_editor.action_editor.action_group.expander.preview)
        self.right_area.key_editor.action_editor.action_group.expander.actions.pop(index)
        return True
    
    def on_dnd_motion(self, drop_target, x, y):
        self.right_area.key_editor.action_editor.action_group.expander.add_drop_preview(self.index)

        return Gdk.DragAction.MOVE

    def on_click(self, button):
        self.right_area.show_action_configurator()


class AddActionButtonRow(Adw.PreferencesRow):
    def __init__(self, expander, **kwargs):
        super().__init__(**kwargs, css_classes=["no-padding", "add-button"])
        self.expander = expander

        self.button = Gtk.Button(hexpand=True, vexpand=True, overflow=Gtk.Overflow.HIDDEN,
                                 css_classes=["no-margin", "invisible"],
                                 label="Add Action",
                                 margin_bottom=5, margin_top=5)
        self.button.connect("clicked", self.on_click)
        self.set_child(self.button)

    def on_click(self, button):
        self.expander.action_group.right_area.set_visible_child_name("action_chooser")