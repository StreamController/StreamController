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
import os
import json
from loguru import logger as log
from copy import copy

# Import globals
import globals as gl

class Page(dict):
    def __init__(self, json_path, deck_controller, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.json_path = json_path
        self.deck_controller = deck_controller

        # Dir that contains all actions this allows us to keep them at reload
        self.action_objects = {}
        self.loaded = False

        self.load()

    def load(self):
        with open(self.json_path) as f:
            self.update(json.load(f))
        # self.load_actions()
            self.load_action_objects()

            # Call on_ready for all actions
            if not self.loaded:
                self.call_actions_ready()
        self.loaded = True

    def save(self):
        without_objects = self.get_without_action_objects()
        # Make keys last element
        self.move_key_to_end(without_objects, "keys")
        with open(self.json_path, "w") as f:
            json.dump(without_objects, f, indent=4)

    def move_key_to_end(self, dictionary, key):
        if key in self:
            value = self.pop(key)
            self[key] = value

    def set_background(self, file_path, loop=True, fps=30, show=True):
        background = {
            "show": show,
            "path": file_path,
            "loop": loop,
            "fps": fps
        }
        self["background"] = background
        self.save()

    def load_action_objects(self):
        for key in self["keys"]:
            if "actions" not in self["keys"][key]:
                continue
            for i, action in enumerate(self["keys"][key]["actions"]):
                action_class = gl.plugin_manager.get_action_from_action_string(action["name"])
                if action_class is None:
                    return
                self.action_objects.setdefault(key, {})

                old_object = self.action_objects[key].get(i)
                if isinstance(old_object, action_class):
                    # Action already exists - keep it
                    continue
                
                action_object = action_class(deck_controller=self.deck_controller, page=self, coords=key)
                #TODO: Change this to a list because there is no reason for it to be a dict
                self.action_objects[key][i] = action_object

    def get_without_action_objects(self):
        dictionary = copy(self)
        for key in dictionary["keys"]:
            if "actions" not in dictionary["keys"][key]:
                continue
            for action in dictionary["keys"][key]["actions"]:
                if "object" in action:
                    del action["object"]

        return dictionary

    def get_all_actions(self):
        actions = []
        for key in self.action_objects:
            for action in self.action_objects[key].values():
                actions.append(action)
        return actions
    
    def get_all_actions_for_key(self, key):
        actions = []
        if key in self.action_objects:
            for action in self.action_objects[key].values():
                actions.append(action)
        return actions
    
    def get_settings_for_action(self, action_object, coords: list = None):
        if coords is None:
            for key in self["keys"]:
                for i, action in enumerate(self["keys"][key]["actions"]):
                    if not key in self.action_objects:
                        break
                    if not i in self.action_objects[key]:
                        break
                    if self.action_objects[key][i] == action_object:
                        return action["settings"]
        else:
            for i, action in enumerate(self["keys"][coords]["actions"]):
                if not coords in self.action_objects:
                    break
                if not i in self.action_objects[coords]:
                    break
                if self.action_objects[coords][i] == action_object:
                    return action["settings"]
                
    def set_settings_for_action(self, action_object, settings: dict, coords: list = None):
        if coords is None:
            for key in self["keys"]:
                for i, action in enumerate(self["keys"][key]["actions"]):
                    if self.action_objects[key][i] == action_object:
                        self["keys"][key]["actions"][i]["settings"] = settings
        else:
            for i, action in enumerate(self["keys"][coords]["actions"]):
                if self.action_objects[coords][i] == action_object:
                    self["keys"][coords]["actions"][i]["settings"] = settings

    def has_key_a_image_controlling_action(self, page_coords: str):
        for key in self.action_objects:
            for action in self.action_objects[key].values():
                if action.CONTROLS_KEY_IMAGE:
                    return True
        return False

    def call_actions_ready(self):
        for action in self.get_all_actions():
            if hasattr(action, "on_ready"):
                action.on_ready()