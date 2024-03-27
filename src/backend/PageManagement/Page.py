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
import gc
import os
import json
import threading
import time
from loguru import logger as log
from copy import copy
import shutil

# Import globals
import globals as gl

# Import typing
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from src.backend.PluginManager.ActionHolder import ActionHolder
    from src.backend.PluginManager.ActionBase import ActionBase

class Page:
    def __init__(self, json_path, deck_controller, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.dict = {}

        self.json_path = json_path
        self.deck_controller = deck_controller

        # Dir that contains all actions this allows us to keep them at reload
        self.action_objects = {}

        self.load(load_from_file=True)

    def get_name(self) -> str:
        return os.path.splitext(os.path.basename(self.json_path))[0]

    def load(self, load_from_file: bool = False):
        start = time.time()
        if load_from_file:
            with open(self.json_path) as f:
                self.dict.update(json.load(f))
        self.load_action_objects()

        # Call on_ready for all actions
        self.call_actions_ready()
        end = time.time()
        log.debug(f"Loaded page {self.get_name()} in {end - start:.2f} seconds")

    def save(self):
        # Make backup in case something goes wrong
        self.make_backup()

        without_objects = self.get_without_action_objects()
        # Make keys last element
        self.move_key_to_end(without_objects, "keys")
        with open(self.json_path, "w") as f:
            json.dump(without_objects, f, indent=4)

    def make_backup(self):
        os.makedirs(os.path.join(gl.DATA_PATH, "pages","backups"), exist_ok=True)

        src_path = self.json_path
        dst_path = os.path.join(gl.DATA_PATH, "pages","backups", os.path.basename(src_path))

        # Check if json in src is valid
        with open(src_path) as f:
            try:
                json.load(f)
            except json.decoder.JSONDecodeError as e:
                log.error(f"Invalid json in {src_path}: {e}")
                return

        shutil.copy2(src_path, dst_path)

    def move_key_to_end(self, dictionary, key):
        if key in self.dict:
            value = self.dict.pop(key)
            self.dict[key] = value

    def set_background(self, file_path):
        self.dict.setdefault("background", {})
        self.dict["background"]["path"] = file_path
        self.save()

    def load_action_objects(self):
        # Store loaded action objects
        self.loaded_action_objects = copy(self.action_objects)

        add_threads: list[threading.Thread] = []

        # Load action objects
        self.action_objects = {}
        for key in self.dict.get("keys", {}):
            if "actions" not in self.dict["keys"][key]:
                continue
            for i, action in enumerate(self.dict["keys"][key]["actions"]):
                if action.get("id") is None:
                    continue

                self.action_objects.setdefault(key, {})

                action_holder = gl.plugin_manager.get_action_holder_from_id(action["id"])
                if action_holder is None:
                    self.action_objects[key][i] = NoActionHolderFound(id=action["id"])
                    continue
                action_class = action_holder.action_base
                
                if action_class is None:
                    self.action_objects[key][i] = NoActionHolderFound(id=action["id"])
                    continue

                old_object = self.action_objects[key].get(i)
                if old_object is not None:
                    if isinstance(old_object, action_class) and not isinstance(old_object, NoActionHolderFound):    
                        # Action already exists - keep it
                        continue
                
                if i in self.loaded_action_objects.get(key, []):
                    if not isinstance(self.loaded_action_objects.get(key, [i])[i], NoActionHolderFound):
                        self.action_objects[key][i] = self.loaded_action_objects[key][i]
                        continue

                # action_object = action_holder.init_and_get_action(deck_controller=self.deck_controller, page=self, coords=key)
                # self.action_objects[key][i] = action_object
                if self.deck_controller.coords_to_index(key.split("x")) > self.deck_controller.deck.key_count():
                    continue
                thread = threading.Thread(target=self.add_action_object_from_holder, args=(action_holder, key, i), name=f"add_action_object_from_holder_{key}_{i}")
                thread.start()
                add_threads.append(thread)

        all_threads_finished = False
        while not all_threads_finished:
            all_threads_finished = True
            for thread in add_threads:
                if thread.is_alive():
                    all_threads_finished = False
                    break
            time.sleep(0.02)

    def move_actions(self, from_key: str, to_key: str):
        from_actions = self.action_objects.get(from_key, {})

        for action in from_actions.values():
            action: "ActionBase" = action
            action.key_index = self.deck_controller.coords_to_index(to_key.split("x"))
            action.page_coords = to_key


    def switch_actions_of_keys(self, key_1: str, key_2: str):
        key_1_actions = self.action_objects.get(key_1, {})
        key_2_actions = self.action_objects.get(key_2, {})

        for action in key_1_actions.values():
            action: "ActionBase" = action
            action.key_index = self.deck_controller.coords_to_index(key_2.split("x"))
            action.page_coords = key_2

        for action in key_2_actions.values():
            action: "ActionBase" = action
            action.key_index = self.deck_controller.coords_to_index(key_1.split("x"))
            action.page_coords = key_1

        # Change in action_objects
        self.action_objects[key_1] = key_2_actions
        self.action_objects[key_2] = key_1_actions


    def add_action_object_from_holder(self, action_holder: "ActionHolder", key: str, i: int):
        action_object = action_holder.init_and_get_action(deck_controller=self.deck_controller, page=self, coords=key)
        if action_object is None:
            return
        self.action_objects[key][i] = action_object

    def remove_plugin_action_objects(self, plugin_id: str) -> bool:
        plugin_obj = gl.plugin_manager.get_plugin_by_id(plugin_id)
        if plugin_obj is None:
            return False
        for key in list(self.action_objects.keys()):
            for index in list(self.action_objects[key].keys()):
                if isinstance(self.action_objects[key][index], NoActionHolderFound):
                    continue
                if self.action_objects[key][index].plugin_base == plugin_obj:
                    # Remove object
                    action = self.action_objects[key][index]
                    del action

                    # Remove action from action_objects
                    del self.action_objects[key][index]

        return True
    
    def get_keys_with_plugin(self, plugin_id: str):
        plugin_obj = gl.plugin_manager.get_plugin_by_id(plugin_id)
        if plugin_obj is None:
            return []
        
        keys = []
        for key in self.action_objects:
            for action in self.action_objects[key].values():
                if isinstance(action, NoActionHolderFound):
                    continue
                if action.plugin_base == plugin_obj:
                    keys.append(key)

        return keys

    def remove_plugin_actions_from_json(self, plugin_id: str): 
        for key in self.dict["keys"]:
            for i, action in enumerate(self.dict["keys"][key]["actions"]):
                # Check if the action is from the plugin by using the plugin id before the action name
                if self.dict["keys"][key]["actions"].split("::")[0] == plugin_id:
                    del self.dict["keys"][key]["actions"][i]

        self.save()

    def get_without_action_objects(self):
        dictionary = copy(self.dict)
        for key in dictionary.get("keys", {}):
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
                if action is None:
                    continue
                if isinstance(action, NoActionHolderFound):
                    continue
                actions.append(action)
        return actions
    
    def get_all_actions_for_key(self, key):
        actions = []
        if key in self.action_objects:
            for action in self.action_objects[key].values():
                if isinstance(action, NoActionHolderFound) or action is None:
                    continue
                actions.append(action)
        return actions
    
    def get_settings_for_action(self, action_object, coords: list = None):
        if coords is None:
            for key in self.dict["keys"]:
                for i, action in enumerate(self.dict["keys"][key]["actions"]):
                    if not key in self.action_objects:
                        break
                    if not i in self.action_objects[key]:
                        break
                    if self.action_objects[key][i] == action_object:
                        return action["settings"]
        else:
            for i, action in enumerate(self.dict["keys"][coords]["actions"]):
                if not coords in self.action_objects:
                    break
                if not i in self.action_objects[coords]:
                    break
                if self.action_objects[coords][i] == action_object:
                    return action["settings"]
        return {}
                
    def set_settings_for_action(self, action_object, settings: dict, coords: list = None):
        if coords is None:
            for key in self.dict["keys"]:
                for i, action in enumerate(self.dict["keys"][key]["actions"]):
                    if self.action_objects[key][i] == action_object:
                        self.dict["keys"][key]["actions"][i]["settings"] = settings
        else:
            for i, action in enumerate(self.dict["keys"][coords]["actions"]):
                if self.action_objects[coords][i] == action_object:
                    self.dict["keys"][coords]["actions"][i]["settings"] = settings

    def has_key_an_image_controlling_action(self, page_coords: str):
        if page_coords not in self.action_objects:
            return False
        for action in self.action_objects[page_coords].values():
            if action.CONTROLS_KEY_IMAGE:
                return True
        return False

    def call_actions_ready(self):
        for action in self.get_all_actions():
            if hasattr(action, "on_ready"):
                if not action.on_ready_called:
                    action.on_ready()
                    action.on_ready_called = True

    def clear_action_objects(self):
        for key in self.action_objects:
            for i, action in enumerate(list(self.action_objects[key])):
                self.action_objects[key][i].page = None
                self.action_objects[key][i] = None
                refs = gc.get_referrers(self.action_objects[key][i])
                r2 = gc.get_referents(self.action_objects[key][i])
                n = len(refs)
                del self.action_objects[key][i]
        self.action_objects = {}

    def get_name(self):
        return os.path.splitext(os.path.basename(self.json_path))[0]
    
    def get_pages_with_same_json(self, get_self: bool = False) -> list:
        pages: list[Page]= []
        for controller in gl.deck_manager.deck_controller:
            if controller.active_page is None:
                continue
            if controller.active_page == self and not get_self:
                continue
            if controller.active_page.json_path == self.json_path:
                pages.append(controller.active_page)
        return pages
    
    def reload_similar_pages(self, page_coords=None, reload_self: bool = False,
                             load_brightness: bool = True, load_screensaver: bool = True, load_background: bool = True, load_keys: bool = True):
        self.save()
        for page in self.get_pages_with_same_json(get_self=reload_self):
            page.load(load_from_file=True)
            if page_coords is None:
                page.deck_controller.load_page(page, load_brightness, load_screensaver, load_background, load_keys)
            else:
                key_index = page.deck_controller.coords_to_index(page_coords.split("x"))
                # Reload only given key
                page.deck_controller.load_key(key_index, page.deck_controller.active_page)

    def get_action_comment(self, page_coords: str, index: int):
        if page_coords in self.action_objects:
            if index in self.action_objects[page_coords]:
                try:
                    return self.dict["keys"][page_coords]["actions"][index].get("comment")
                except:
                    return ""
            
    def set_action_comment(self, page_coords: str, index: int, comment: str):
        if page_coords in self.action_objects:
            if index in self.action_objects[page_coords]:
                self.dict["keys"][page_coords]["actions"][index]["comment"] = comment
                self.save()

    def fix_action_objects_order(self, page_coords) -> None:
        """
        #TODO: Switch to list instead of dict to avoid this
        """
        if page_coords not in self.action_objects:
            return
        
        actions = list(self.action_objects[page_coords].values())

        d = self.dict.copy()

        self.action_objects[page_coords] = {}
        for i, action in enumerate(actions):
            self.action_objects[page_coords][i] = action

        new_d = self.dict

class NoActionHolderFound:
    def __init__(self, id: str):
        self.id = id