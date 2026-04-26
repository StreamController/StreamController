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
from copy import copy
from typing import TYPE_CHECKING

import gi

import globals as gl
from GtkHelper.GtkHelper import BetterExpander
from src.backend.DeckManagement.InputIdentifier import InputIdentifier
from src.backend.PageManagement.Page import ActionOutdated, NoActionHolderFound
from src.backend.PluginManager.ActionCore import ActionCore
from src.windows.mainWindow.elements.Sidebar.elements.ActionManagerParts.ActionRow import ActionRow
from src.windows.mainWindow.elements.Sidebar.elements.ActionManagerParts.AddActionButtonRow import (
    AddActionButtonRow,
)
from src.windows.mainWindow.elements.Sidebar.elements.ActionMissing.MisingActionButtonRow import (
    MissingActionButtonRow,
)
from src.windows.mainWindow.elements.Sidebar.elements.ActionMissing.OutdatedActionRow import (
    OutdatedActionRow,
)

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, GLib

if TYPE_CHECKING:
    from src.windows.mainWindow.elements.Sidebar.elements.ActionManagerParts.ActionGroup import (
        ActionGroup,
    )


class ActionExpanderRow(BetterExpander):
    def __init__(self, action_group: "ActionGroup"):
        super().__init__(title=gl.lm.get("action-editor-header"), subtitle=gl.lm.get("action-editor-expander-subtitle"))
        self.set_expanded(True)
        self.active_identifier = None
        self.action_group = action_group
        self.active_state = None

        self.preview = None

        self.build()

    def build(self):
        self.add_action_button = AddActionButtonRow(self).button
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

    def load_for_actions(self, actions: list[ActionCore]):
        number_of_actions = len(actions)
        for i, action in enumerate(actions):
            if isinstance(action, ActionCore):
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
