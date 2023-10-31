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
    def __init__(self, json_path, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.json_path = json_path
        self.load()

    def load(self):
        with open(self.json_path) as f:
            self.update(json.load(f))
        self.load_actions()

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

    def load_actions(self):
        for key in self["keys"]:
            if "actions" not in self["keys"][key]:
                continue
            for action in self["keys"][key]["actions"]:
                action_object = gl.plugin_manager.get_action_from_action_string(action["name"])
                if action_object == None:
                    log.warning(f"Action {action['name']} not found, skipping")
                    continue
                action_object.settings = action["settings"]
                action["object"] = action_object

    def get_without_action_objects(self):
        dictionary = copy(self)
        for key in dictionary["keys"]:
            if "actions" not in dictionary["keys"][key]:
                continue
            for action in dictionary["keys"][key]["actions"]:
                if "object" in action:
                    del action["object"]

        return dictionary