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

from src.backend.DeckManagement.InputIdentifier import Input, InputIdentifier
from src.backend.DeckManagement.HelperMethods import add_default_keys
from src.windows.Settings.PluginSettingsWindow.PluginSettingsWindow import PluginSettingsWindow

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

    def load_for_identifier(self, identifier: InputIdentifier, state: int):
        self.action_group.load_for_identifier(identifier, state)

class ActionGroup(Adw.PreferencesGroup):
    def __init__(self, sidebar, **kwargs):
        super().__init__(**kwargs)
        self.sidebar = sidebar
        self.active_identifier = None

        self.actions = []

        self.build()

    def build(self):
        self.expander = ActionExpanderRow(self)
        self.add(self.expander)

    def load_for_identifier(self, identifier: InputIdentifier, state: int):
        self.active_identifier = identifier
        self.expander.load_for_identifier(identifier, state)

    def load_for_coords(self, coords: tuple[int, int], state: int):
        self.expander.load_for_coords(coords, state)

    def load_for_screen(self, gesture: str, state: int):
        self.expander.load_for_screen(gesture, state)

    def load_for_dial(self, n: int, state: int):
        self.expander.load_for_dial(n, state)


class ActionExpanderRow(BetterExpander):
    def __init__(self, action_group):
        super().__init__(title=gl.lm.get("action-editor-header"), subtitle=gl.lm.get("action-editor-expander-subtitle"))
        self.set_expanded(True)
        self.active_identifier = None
        self.action_group = action_group
        self.active_state = None

        self.preview = None

        self.build()

    def build(self):
        self.add_action_button = AddActionButtonRow(self)
        self.add_row(self.add_action_button)

    def add_action_row(self, action_name: str, action_id: str, action_category, action_object, comment: str, index: int, total_rows: int, controls_image: bool = False, controls_labels: list[bool] = [False, False, False], controls_background: bool = False):
        action_row = ActionRow(action_name, action_id, action_category, action_object, self.action_group.sidebar, comment, index, controls_image, controls_labels, controls_background, total_rows, self)
        self.add_row(action_row)

    def load_for_identifier(self, identifier: InputIdentifier, state: int):
        if not isinstance(identifier, InputIdentifier):
            raise ValueError("Invalid identifier given to load_for_identifier")
        self.active_state = state
        self.active_identifier = identifier

        self.clear_actions(keep_add_button=True)

        controller = gl.app.main_win.get_active_controller()

        actions = controller.active_page.action_objects.get(identifier.input_type, {}).get(identifier.json_identifier, {}).get(state, {})
        self.load_for_actions(actions.values())

    def load_for_actions(self, actions: list[ActionBase]):
        number_of_actions = len(actions)
        for i, action in enumerate(actions):
            if isinstance(action, ActionBase):
                # Get action comment
                comment = action.page.get_action_comment(index=i,
                                                         state=action.state,
                                                         identifier=action.input_ident)

                controls_image = action.has_image_control()
                controls_background = action.has_background_control()
                controls_labels = action.has_label_controls()

                self.add_action_row(action.action_name, action.action_id, action.plugin_base.plugin_name, action, controls_image=controls_image, controls_labels=controls_labels, controls_background=controls_background, comment=comment, index=i, total_rows=number_of_actions)
            elif isinstance(action, NoActionHolderFound):
                action: NoActionHolderFound
                missing_button_row = MissingActionButtonRow(action.id, action.identifier, self.active_state, i)
                self.add_row(missing_button_row)
            elif isinstance(action, ActionOutdated):
                # No plugin installed for this action
                action: ActionOutdated
                missing_button_row = OutdatedActionRow(action.id, action.identifier, self.active_state, i)
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
        controller = gl.app.main_win.get_active_controller()
        if controller is None:
            return

        actions = controller.active_page.dict[self.active_identifier.input_type][self.active_identifier.json_identifier]["states"][str(self.active_state)]["actions"]
        reordered = self.reorder_index_after(copy(actions), move_index, after_index)

        action_objects = controller.active_page.action_objects[self.active_identifier.input_type][self.active_identifier.json_identifier][self.active_state]
        reordered_action_objects = self.reorder_action_objects(action_objects, move_index, after_index)


        # Reorder in page dict
        controller.active_page.dict[self.active_identifier.input_type][self.active_identifier.json_identifier]["states"][str(self.active_state)]["actions"] = reordered

        # Reorder in action objects
        controller.active_page.action_objects[self.active_identifier.input_type][self.active_identifier.json_identifier][self.active_state] = reordered_action_objects


        ## Update control indices
        action_order_map: dict[int, int] = {}

        for i, action in enumerate(action_objects.values()):
            action_order_map[i] = list(reordered_action_objects.values()).index(action)


        image_control_action_index = controller.active_page.dict[self.active_identifier.input_type][self.active_identifier.json_identifier]["states"][str(self.active_state)].get("image-control-action")
        controller.active_page.dict[self.active_identifier.input_type][self.active_identifier.json_identifier]["states"][str(self.active_state)]["image-control-action"] = action_order_map.get(image_control_action_index, None)

        label_control_actions = controller.active_page.dict[self.active_identifier.input_type][self.active_identifier.json_identifier]["states"][str(self.active_state)].get("label-control-actions")
        for i, label_control_action in enumerate(label_control_actions):
            label_control_actions[i] = action_order_map.get(label_control_action)
        controller.active_page.dict[self.active_identifier.input_type][self.active_identifier.json_identifier]["states"][str(self.active_state)]["label-control-actions"] = label_control_actions
        
        controller.active_page.save()

        controller.load_page(controller.active_page)
 
    def update_comment_for_index(self, action_index):
        visible_child = gl.app.main_win.leftArea.deck_stack.get_visible_child()
        if visible_child is None:
            return
        controller = visible_child.deck_controller
        if controller is None:
            return
        comment = controller.active_page.get_action_comment(identifier=self.active_identifier, index=action_index)
        self.get_rows()[action_index].set_comment(comment)


class ActionRowLabelToggle(Gtk.Button):
    def __init__(self, action_row: "ActionRow"):
        self.action_row = action_row
        super().__init__(tooltip_text="Control which labels are controlled by this action")

        self.build()

    def build(self):
        self.set_css_classes(["blue-toggle-button"])

        self.main_box = Gtk.Box()
        self.set_child(self.main_box)

        self.main_box.append(Gtk.Image(icon_name="format-text-italic-symbolic"))

        self.indicator_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3, valign=Gtk.Align.CENTER, margin_start=5)
        self.main_box.append(self.indicator_box)


        self.indicators: list[Gtk.Box] = []
        for i in range(3):
            indicator = Gtk.Box(css_classes=["action-row-label-toggle-inactive"])
            self.indicator_box.append(indicator)
            self.indicators.append(indicator)

        self.config_buttons: list[Gtk.CheckButton] = []
        self.config_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

        label_names = ["Top", "Center", "Bottom"]
        for i, name in enumerate(label_names):
            check = Gtk.CheckButton(label=name, name=str(i))
            self.config_buttons.append(check)
            if "action-row-label-toggle-active" in self.indicators[i].get_css_classes():
                check.set_active(True)    
            check.connect("toggled", self.on_label_toggled)
            self.config_box.append(check)


        self.popover = Gtk.Popover(child=self.config_box)
        self.main_box.append(self.popover)


        self.connect("clicked", self.on_click)

    def on_click(self, button):
        self.popover.popup()

    def on_label_toggled(self, button: Gtk.CheckButton):
        i = int(button.get_name())

        indicator = self.indicators[i]

        if button.get_active():
            indicator.set_css_classes(["action-row-label-toggle-active"])
        else:
            indicator.set_css_classes(["action-row-label-toggle-inactive"])

        self.action_row.label_toggled(i, button.get_active())

    def connect_signals(self):
        for button in self.config_buttons:
            button.connect("toggled", self.on_label_toggled)

    def disconnect_signals(self):
        for button in self.config_buttons:
            try:
                button.disconnect_by_func(self.on_label_toggled)
            except:
                pass

    def set_active(self, values: list[bool]) -> None:
        self.disconnect_signals()
        for i, value in enumerate(values):
            indicator = self.indicators[i]
            if value:
                indicator.set_css_classes(["action-row-label-toggle-active"])
            else:
                indicator.set_css_classes(["action-row-label-toggle-inactive"])

            self.config_buttons[i].set_active(value)
        self.connect_signals()

    def get_active(self) -> list[bool]:
        return [indicator.get_css_classes() == ["action-row-label-toggle-active"] for indicator in self.indicators]


class ActionRow(Adw.ActionRow):
    def __init__(self, action_name, action_id, action_category, action_object, sidebar: "Sidebar", comment: str, index, controls_image: bool, controls_labels: list[bool], controls_background: bool, total_rows: int, expander: ActionExpanderRow, **kwargs):
        super().__init__(**kwargs, css_classes=["no-padding"])
        self.action_name = action_name
        self.action_id = action_id
        self.action_category = action_category
        self.sidebar: "Sidebar" = sidebar
        self.action_object: "ActionBase" = action_object
        self.comment = comment
        self.index = index
        self.controls_image = controls_image
        self.controls_labels = controls_labels
        self.controls_background = controls_background
        self.active_type = None
        self.active_identifier = None
        self.total_rows = total_rows
        self.expander = expander
        self.build()
        self.update_allow_box_visibility()
        # self.init_dnd() #FIXME: Add drag and drop

    def build(self):
        # self.overlay = Gtk.Overlay()
        # self.set_child(self.overlay)

        # self.button = Gtk.Button(hexpand=True, vexpand=True, overflow=Gtk.Overflow.HIDDEN, css_classes=["no-margin", "invisible", "action-row-button"])
        # self.button.connect("clicked", self.on_click)
        # self.overlay.set_child(self.button)

        self.connect("activated", self.on_click)

        self.set_activatable(True)


        self.main_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, hexpand=True, margin_start=15, margin_end=15, margin_top=15, margin_bottom=15)
        self.set_child(self.main_box)

        self.allow_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, css_classes=["linked"], margin_end=15)
        self.main_box.append(self.allow_box)

        self.allow_image_toggle = Gtk.ToggleButton(css_classes=["blue-toggle-button"], icon_name="image-x-generic-symbolic", active=self.controls_image,
                                                   tooltip_text="Allow action to control the media")
        self.allow_image_toggle.connect("toggled", self.on_allow_image_toggled)
        self.allow_box.append(self.allow_image_toggle)

        self.allow_background_toggle = Gtk.ToggleButton(css_classes=["blue-toggle-button"], icon_name="color-select-symbolic", active=self.controls_background,
                                                        tooltip_text="Allow action to control the background color")
        self.allow_background_toggle.connect("toggled", self.on_allow_background_toggled)
        self.allow_box.append(self.allow_background_toggle)

        self.allow_label_toggle = ActionRowLabelToggle(self)
        self.allow_label_toggle.set_active(self.controls_labels)
        self.allow_box.append(self.allow_label_toggle)
        
        self.left_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, hexpand=True, valign=Gtk.Align.CENTER)
        self.main_box.append(self.left_box)

        self.left_top_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, hexpand=True)
        self.left_box.append(self.left_top_box)

        self.left_bottom_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, hexpand=True)
        self.left_box.append(self.left_bottom_box)

        self.label = Gtk.Label(label=f"<b>{self.action_name}</b> <span color=\"#979797\">({self.action_category})</span>", use_markup=True, xalign=0, hexpand=False, margin_end=5,
                               wrap_mode=Pango.WrapMode.WORD_CHAR, wrap=True)
        self.left_top_box.append(self.label)

        self.comment_label = Gtk.Label(label=self.comment, xalign=0, sensitive=False, ellipsize=Pango.EllipsizeMode.END, margin_end=60)
        self.left_bottom_box.append(self.comment_label)

        if self.comment in ["", None]:
            self.left_bottom_box.set_visible(False)
            # self.left_top_box.set_

        ## Edit buttons
        self.button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, halign=Gtk.Align.END, valign=Gtk.Align.CENTER, css_classes=["linked"])
        self.main_box.append(self.button_box)
        # self.overlay.add_overlay(self.button_box)

        self.up_button = Gtk.Button(icon_name="go-up-symbolic")
        self.up_button.connect("clicked", self.on_click_up)
        self.button_box.append(self.up_button)

        self.down_button = Gtk.Button(icon_name="go-down-symbolic")
        self.down_button.connect("clicked", self.on_click_down)
        self.button_box.append(self.down_button)

        self.remove_button = Gtk.Button(icon_name="user-trash-symbolic", css_classes=["destructive-action"])
        # self.button_box.append(self.remove_button) #TODO
        # self.remove_button.connect("clicked", self.on_click_remove)

    def update_allow_box_visibility(self):
        self.allow_box.set_visible(True) #TODO
        return
        if self.expander.active_identifier is None:
            self.allow_box.set_visible(False)
            return
        hide = self.controls_image and any(self.controls_labels) and (self.total_rows == 1)
        self.allow_box.set_visible(not hide)

    def on_allow_image_toggled(self, button):
        for child in self.expander.get_rows():
            if child is self:
                continue
            if not isinstance(child, ActionRow):
                continue
            child.set_image_toggled(False)


        controller = gl.app.main_win.get_active_controller()
        if controller is None:
            return
        page = controller.active_page

        input_state = self.action_object.get_input().states.get(self.expander.active_state)
        if input_state is None:
            log.error("Input state not found")
            return
        
        new_value = self.index if button.get_active() else None
        input_state.action_permission_manager.set_image_control_index(new_value, True, True)

        page.reload_similar_pages(identifier=self.action_object.input_ident, reload_self=True)

    def on_allow_background_toggled(self, button):
        for child in self.expander.get_rows():
            if child is self:
                continue
            if not isinstance(child, ActionRow):
                continue
            child.set_background_toggled(False)

        controller = gl.app.main_win.get_active_controller()
        if controller is None:
            return
        page = controller.active_page

        input_state = self.action_object.get_input().states.get(self.expander.active_state)
        if input_state is None:
            log.error("Input state not found")
            return
        
        new_value = self.index if button.get_active() else None
        input_state.action_permission_manager.set_background_control_index(new_value, True, True)

        page.reload_similar_pages(identifier=self.action_object.input_ident, reload_self=True)

    def label_toggled(self, i, value):
        for child in self.expander.get_rows():
            if child is self:
                continue
            if not isinstance(child, ActionRow):
                continue
            # child.set_label_toggled(False)
            active = child.allow_label_toggle.get_active()
            active[i] = False
            child.allow_label_toggle.set_active(active)

        controller = gl.app.main_win.get_active_controller()
        if controller is None:
            return
       
        input_state = self.action_object.get_input().states.get(self.expander.active_state)
        if input_state is None:
            log.error("Input state not found")
            return
        
        value = self.action_object.get_own_action_index() if value else None
        
        input_state.action_permission_manager.set_label_control_index(i, value, True, True)

    def set_image_toggled(self, value: bool):
        try:
            self.allow_image_toggle.disconnect_by_func(self.on_allow_image_toggled)
        except:
            pass

        self.allow_image_toggle.set_active(value)

        self.allow_image_toggle.connect("toggled", self.on_allow_image_toggled)

    def set_background_toggled(self, value: bool):
        try:
            self.allow_background_toggle.disconnect_by_func(self.on_allow_background_toggled)
        except:
            pass

        self.allow_background_toggle.set_active(value)

        self.allow_background_toggle.connect("toggled", self.on_allow_background_toggled)

    def set_label_toggled(self, value: bool):
        try:
            self.allow_label_toggle.disconnect_by_func(self.on_allow_label_toggled)
        except:
            pass

        self.allow_label_toggle.set_active(value)

        self.allow_label_toggle.connect("toggled", self.on_allow_label_toggled)
        
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
        
    def on_click_remove(self, button):
        visible_child = gl.app.main_win.leftArea.deck_stack.get_visible_child()
        if visible_child is None:
            return
        controller = visible_child.deck_controller
        if controller is None:
            return
        page = controller.active_page

        # Remove from action_objects
        del page.action_objects[self.action_object.type][self.action_object.identifier][self.index]
        page.fix_action_objects_order(self.action_object.type, self.action_object.identifier)

        # Remove from page json
        page.dict[self.action_object.type][self.action_object.identifier]["actions"].pop(self.index)
        page.save()

        page.reload_similar_pages(type=self.action_object.type, identifier=self.action_object.identifier)
        page.reload_similar_pages()

        if hasattr(self.action_object, "on_removed_from_cache"):
            self.action_object.on_removed_from_cache()

        self.action_object = None
        del self.action_object

        self.get_parent().remove(self)
            
        
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
        self.expander: ActionExpanderRow = expander

        self.button = Gtk.Button(hexpand=True, vexpand=True, overflow=Gtk.Overflow.HIDDEN,
                                 css_classes=["no-margin", "invisible"],
                                 label=gl.lm.get("action-editor-add-new-action"),
                                 margin_bottom=5, margin_top=5)
        self.button.connect("clicked", self.on_click)
        self.action_name = "Add Action"
        self.set_child(self.button)

    def on_click(self, button):
        self.expander.action_group.sidebar.let_user_select_action(callback_function=self.add_action, identifier=self.expander.active_identifier)

    def add_action(self, action_class):
        log.trace(f"Adding action: {action_class}")

        # Gather data
        # action_string = gl.plugin_manager.get_action_string_from_action(action_class)
        active_page = gl.app.main_win.get_active_page()
        if active_page is None:
            return
        
        add_default_keys(active_page.dict, [self.expander.active_identifier.input_type, self.expander.active_identifier.json_identifier, "states", str(self.expander.active_state)])
        state_dict = active_page.dict[self.expander.active_identifier.input_type][self.expander.active_identifier.json_identifier]["states"][str(self.expander.active_state)]
        state_dict.setdefault("actions", [])

        # Add action
        state_dict["actions"].append({
            "id": action_class.action_id,
            "settings": {}
        })

        if len(state_dict["actions"]) == 1:
            state_dict.setdefault("image-control-action", 0)
            state_dict.setdefault("label-control-actions", [0, 0, 0])
            state_dict.setdefault("background-control-action", 0)

        # Save page
        active_page.save()
        # Reload page to add an object to the new action
        active_page.load()
        # Reload the key on all decks
        active_page.reload_similar_pages(identifier=self.expander.active_identifier, reload_self=True)

        # Reload ui
        self.expander.load_for_identifier(self.expander.active_identifier, self.expander.active_state)

        rows = self.expander.get_rows()
        if len(rows) < 2:
            return

        last_row = rows[-2]  # -1 is the add button
        action = last_row.action_object

        # Open Action Config Screen
        settings = gl.settings_manager.get_app_settings()
        if settings.get("ui", {}).get("auto-open-action-config", True):
            if action and action.has_configuration:
                gl.app.main_win.sidebar.action_configurator.load_for_action(last_row.action_object, last_row.index)
                gl.app.main_win.sidebar.show_action_configurator()

        # Open Plugin Settings Window
        if action and action.plugin_base.has_plugin_settings and action.plugin_base.first_setup:
            settings_window = PluginSettingsWindow(action.plugin_base)
            settings_window.present(gl.app.get_active_window())

            settings = action.plugin_base.get_settings()
            settings["first-setup"] = False
            action.plugin_base.set_settings(settings)
            action.plugin_base.first_setup = False