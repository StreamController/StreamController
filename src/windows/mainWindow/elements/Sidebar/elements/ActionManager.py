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
from gi.repository import Gtk, Adw, Gdk, GLib, Pango

# Import Python modules
from loguru import logger as log
from copy import copy
import asyncio
import threading

# Import globals
import globals as gl

# Import own modules
from src.backend.PluginManager.ActionBase import ActionBase
from GtkHelper.GtkHelper import BetterExpander
from src.backend.PageManagement.Page import NoActionHolderFound, ActionOutdated
from src.windows.mainWindow.elements.Sidebar.elements.ActionMissing.MisingActionButtonRow import MissingActionButtonRow
from src.windows.mainWindow.elements.Sidebar.elements.ActionMissing.OutdatedActionRow import OutdatedActionRow

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from src.windows.mainWindow.elements.Sidebar.Sidebar import Sidebar

class ActionManager(Gtk.Box):
    def __init__(self, sidebar, **kwargs):
        self.sidebar = sidebar
        super().__init__(**kwargs)
        self.build()

    def build(self):
        self.clamp = Adw.Clamp()
        self.append(self.clamp)

        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, hexpand=True)
        self.clamp.set_child(self.main_box)

        self.action_group = ActionGroup(self.sidebar)
        self.main_box.append(self.action_group)

        self.main_box.set_margin_bottom(50)

    def load_for_coords(self, coords):
        self.action_group.load_for_coords(coords)

class ActionGroup(Adw.PreferencesGroup):
    def __init__(self, sidebar, **kwargs):
        super().__init__(**kwargs)
        self.sidebar = sidebar

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
        super().__init__(title=gl.lm.get("action-editor-header"), subtitle=gl.lm.get("action-editor-expander-subtitle"))
        self.set_expanded(True)
        self.action_group = action_group
        self.active_coords = None

        self.preview = None

        self.build()

    def build(self):
        self.add_action_button = AddActionButtonRow(self)
        self.add_row(self.add_action_button)

    def add_action_row(self, action_name: str, action_id: str, action_category, action_object, comment: str, index: int, total_rows: int):
        action_row = ActionRow(action_name, action_id, action_category, action_object, self.action_group.sidebar, comment, index, total_rows, self)
        self.add_row(action_row)

    def load_for_coords(self, coords):
        self.clear_actions(keep_add_button=True)
        self.active_coords = coords
        page_coords = f"{coords[0]}x{coords[1]}"
        controller = self.action_group.sidebar.main_window.leftArea.deck_stack.get_visible_child().deck_controller
        if page_coords not in controller.active_page.action_objects:
            return
        
        
        number_of_actions = len(controller.active_page.action_objects[page_coords])
        for i, key in enumerate(controller.active_page.action_objects[page_coords]):
            action = controller.active_page.action_objects[page_coords][key]
            if isinstance(action, ActionBase):
                # Get action comment
                comment = controller.active_page.get_action_comment(page_coords=page_coords, index=key)

                self.add_action_row(action.action_name, action.action_id, action.plugin_base.plugin_name, action, comment=comment, index=i, total_rows=number_of_actions)
            elif isinstance(action, NoActionHolderFound):
                missing_button_row = MissingActionButtonRow(action.id, page_coords, i)
                self.add_row(missing_button_row)
            elif isinstance(action, ActionOutdated):
                # No plugin installed for this action
                missing_button_row = OutdatedActionRow(action.id, page_coords, i)
                self.add_row(missing_button_row)
                

        # Place add button at the end
        if len(self.get_rows()) > 0:
            self.reorder_child_after(self.add_action_button, self.get_rows()[-1])

    def clear_actions(self, keep_add_button=False):
        for child in self.get_rows():
            if hasattr(child, "action_object"):
                child.action_object = None
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

    def update_indices(self):
        for i, row in enumerate(self.get_rows()):
            row.index = i

    def reorder_index_after(self, lst, move_index, after_index):
        if move_index < 0 or move_index >= len(lst):
            raise ValueError("Move index out of range.")
        
        if after_index < 0 or after_index >= len(lst):
            raise ValueError("After index out of range.")

        move_item = lst.pop(move_index)
        lst.insert(after_index + 1 if move_index > after_index else after_index, move_item)
        
        return lst
    
    def reorder_action_objects(self, action_objects, move_index, after_index):
        objects = list(action_objects.values())
        reordered = self.reorder_index_after(objects, move_index, after_index)

        new = {}
        for i, obj in enumerate(reordered):
            new[i] = obj

        return new


    def update_action_objects_order(self) -> None:
        new_objects = {}
        for i, row in enumerate(self.get_rows()):
            if not isinstance(row, ActionRow):
                continue
            new_objects[i] = row.action_object


    def reorder_actions(self, move_index, after_index):
        controller = self.action_group.sidebar.main_window.leftArea.deck_stack.get_visible_child().deck_controller
        page_coords = f"{self.active_coords[0]}x{self.active_coords[1]}"

        actions = controller.active_page.dict["keys"][page_coords]["actions"]

        reordered = self.reorder_index_after(actions, move_index, after_index)
        controller.active_page.dict["keys"][page_coords]["actions"] = reordered
        controller.active_page.save()
        # a = controller.active_page.action_objects
        # controller.active_page.action_objects = {}
        # controller.active_page.load_action_objects()

        action_objects = controller.active_page.action_objects[page_coords]

        reordered = self.reorder_action_objects(action_objects, move_index, after_index)
        controller.active_page.action_objects[page_coords] = reordered


        controller.load_page(controller.active_page)

    def update_comment_for_index(self, action_index):
        controller = self.action_group.sidebar.main_window.leftArea.deck_stack.get_visible_child().deck_controller
        page_coords = f"{self.active_coords[0]}x{self.active_coords[1]}"
        comment = controller.active_page.get_action_comment(page_coords=page_coords, index=action_index)
        self.get_rows()[action_index].set_comment(comment)


        

class ActionRow(Adw.PreferencesRow):
    def __init__(self, action_name, action_id, action_category, action_object, sidebar: "Sidebar", comment: str, index, total_rows: int, expander: ActionExpanderRow, **kwargs):
        super().__init__(**kwargs, css_classes=["no-padding"])
        self.action_name = action_name
        self.action_id = action_id
        self.action_category = action_category
        self.sidebar: "Sidebar" = sidebar
        self.action_object = action_object
        self.comment = comment
        self.index = index
        self.active_coords = None
        self.total_rows = total_rows
        self.expander = expander
        self.build()
        self.init_dnd()

    def build(self):
        self.overlay = Gtk.Overlay()
        self.set_child(self.overlay)

        self.button = Gtk.Button(hexpand=True, vexpand=True, overflow=Gtk.Overflow.HIDDEN, css_classes=["no-margin", "invisible", "action-row-button"])
        self.button.connect("clicked", self.on_click)
        self.overlay.set_child(self.button)


        self.main_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, hexpand=True, margin_start=15, margin_end=15, margin_top=15, margin_bottom=15)
        self.button.set_child(self.main_box)

        self.left_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, hexpand=True, valign=Gtk.Align.CENTER)
        self.main_box.append(self.left_box)

        self.left_top_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, hexpand=True)
        self.left_box.append(self.left_top_box)

        self.left_bottom_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, hexpand=True)
        self.left_box.append(self.left_bottom_box)

        self.name_label = Gtk.Label(label=self.action_name, xalign=0, css_classes=["bold"], hexpand=False, margin_end=5)
        self.left_top_box.append(self.name_label)

        self.category_label = Gtk.Label(label=f"({self.action_category})", xalign=0, sensitive=False, hexpand=False)
        self.left_top_box.append(self.category_label)

        self.comment_label = Gtk.Label(label=self.comment, xalign=0, sensitive=False, ellipsize=Pango.EllipsizeMode.END, margin_end=60)
        self.left_bottom_box.append(self.comment_label)

        if self.comment in ["", None]:
            self.left_bottom_box.set_visible(False)
            # self.left_top_box.set_

        ## Move buttons
        self.button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, halign=Gtk.Align.END, valign=Gtk.Align.CENTER, margin_end=10, css_classes=["linked"])
        self.overlay.add_overlay(self.button_box)

        self.up_button = Gtk.Button(icon_name="go-up-symbolic")
        self.up_button.connect("clicked", self.on_click_up)
        self.button_box.append(self.up_button)

        self.down_button = Gtk.Button(icon_name="go-down-symbolic")
        self.down_button.connect("clicked", self.on_click_down)
        self.button_box.append(self.down_button)


    def get_own_index(self) -> int:
        return self.expander.get_index_of_child(self)

    def on_click_up(self, button):
        one_up_child = self.expander.get_rows()[self.index - 1]
        if isinstance(one_up_child, AddActionButtonRow):
            return
        self.expander.reorder_child_after(self, one_up_child)
        self.expander.reorder_actions(self.index - 1, self.index)

        # self.expander.update_indices()


    def on_click_down(self, button):
        one_down_child = self.expander.get_rows()[self.index + 1]
        if isinstance(one_down_child, AddActionButtonRow):
            return
        self.expander.reorder_child_after(self, one_down_child)
        self.expander.reorder_actions(self.index, self.index + 1)

        # self.expander.update_indices()
        
            
        
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
        
        self.sidebar.key_editor.action_editor.action_group.expander.reorder_child_after(value, self)
        return True
        # Remove preview
        index = self.sidebar.key_editor.action_editor.action_group.expander.get_index_of_child(self.sidebar.key_editor.action_editor.action_group.expander.preview)
        self.sidebar.key_editor.action_editor.action_group.expander.remove(self.sidebar.key_editor.action_editor.action_group.expander.preview)
        self.sidebar.key_editor.action_editor.action_group.expander.actions.pop(index)
        return True
    
    def on_dnd_motion(self, drop_target, x, y):
        if y > self.get_height() / 2:
            self.sidebar.key_editor.action_editor.action_group.expander.add_drop_preview(self.index-1)
        else:
            self.sidebar.key_editor.action_editor.action_group.expander.add_drop_preview(self.index)
        return Gdk.DragAction.MOVE


        self.sidebar.key_editor.action_editor.action_group.expander.add_drop_preview(self.index)

        return Gdk.DragAction.MOVE

    def on_click(self, button):
        self.sidebar.action_configurator.load_for_action(self.action_object, self.index)
        self.sidebar.show_action_configurator()

    def update_comment(self, comment: str):
        self.comment = comment
        # Update ui
        if comment is None:
            comment = ""
            self.left_bottom_box.set_visible(False)
        else:
            self.left_bottom_box.set_visible(True)

        self.comment_row.set_text(comment)


class AddActionButtonRow(Adw.PreferencesRow):
    def __init__(self, expander: ActionExpanderRow, **kwargs):
        super().__init__(**kwargs, css_classes=["no-padding", "add-button"])
        self.expander = expander

        self.button = Gtk.Button(hexpand=True, vexpand=True, overflow=Gtk.Overflow.HIDDEN,
                                 css_classes=["no-margin", "invisible"],
                                 label=gl.lm.get("action-editor-add-new-action"),
                                 margin_bottom=5, margin_top=5)
        self.button.connect("clicked", self.on_click)
        self.action_name = "Add Action"
        self.set_child(self.button)

    def on_click(self, button):
        self.expander.action_group.sidebar.let_user_select_action(callback_function=self.add_action)

    def add_action(self, action_class):
        log.trace(f"Adding action: {action_class}")

        # Gather data
        # action_string = gl.plugin_manager.get_action_string_from_action(action_class)
        active_controller = self.expander.action_group.sidebar.main_window.leftArea.deck_stack.get_visible_child().deck_controller
        active_page = active_controller.active_page
        page_coords = f"{self.expander.active_coords[0]}x{self.expander.active_coords[1]}"

        # Set missing values
        active_page.dict.setdefault("keys", {})
        active_page.dict["keys"].setdefault(page_coords, {})
        active_page.dict["keys"][page_coords].setdefault("actions", [])

        # Add action
        active_page.dict["keys"][page_coords]["actions"].append({
            "id": action_class.action_id,
            "settings": {}
        })

        # Save page
        active_page.save()
        # Reload page to add an object to the new action
        active_page.load()
        # Reload the key on all decks
        active_page.reload_similar_pages(page_coords=page_coords)

        # Reload ui
        self.expander.load_for_coords(self.expander.active_coords)

        # Reload key
        controller = self.expander.action_group.sidebar.main_window.leftArea.deck_stack.get_visible_child().deck_controller
        key_index = controller.coords_to_index(self.expander.active_coords)
        controller.load_key(key_index, page=controller.active_page)

        # Open action editor if new action has configuration - qol
        rows = self.expander.get_rows()
        if len(rows) < 2:
            return
        last_row = rows[-2] # -1 is the add button
        if last_row.action_object.has_configuration:
            gl.app.main_win.sidebar.action_configurator.load_for_action(last_row.action_object, last_row.index)
            gl.app.main_win.sidebar.show_action_configurator()