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
from argparse import Action
import gc
import os
import json
import threading
import time
from datetime import datetime, timedelta

from loguru import logger as log
from copy import copy
import shutil

from numpy import isin

# Import globals
from src.backend.DeckManagement.ImageHelpers import crop_key_image_from_deck_sized_image
import globals as gl

from src.backend.PluginManager.ActionBase import ActionBase
from src.backend.DeckManagement.InputIdentifier import Input, InputIdentifier
# Import typing
from typing import TYPE_CHECKING, List

if TYPE_CHECKING:
    from src.backend.DeckManagement.DeckController import LabelManager
    from src.backend.PluginManager.ActionHolder import ActionHolder
    from src.backend.DeckManagement.DeckController import ControllerKeyState, ControllerKey


class Page:
    def __init__(self, json_path, deck_controller, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.dict = {}

        self.json_path: str = json_path
        self.deck_controller = deck_controller

        # Dir that contains all actions this allows us to keep them at reload
        self.action_objects = {}

        self.ready_to_clear = True

        self.file_access_semaphore = threading.Semaphore()

        self.load(load_from_file=True)

    def get_name(self) -> str:
        return os.path.splitext(os.path.basename(self.json_path))[0]
    
    def update_dict(self) -> None:
        """
        Updates the dict without any updates on the action objects.
        Do NOT use if you made changes to the action objects
        """
        self.dict = gl.page_manager.get_page_json(self.json_path)
    
    def load(self, load_from_file: bool = False):
        start = time.time()
        if load_from_file:
            self.update_dict()
        self.load_action_objects()

        # Call on_ready for all actions
        end = time.time()
        log.debug(f"Loaded page {self.get_name()} in {end - start:.2f} seconds")

    def save(self):
        self.file_access_semaphore.acquire()
        # Make backup in case something goes wrong
        self.make_backup()

        without_objects = self.get_without_action_objects()
        # Make keys last element
        for type in Input.KeyTypes:
            self.move_key_to_end(without_objects, type)
        with open(self.json_path, "w") as f:
            json.dump(without_objects, f, indent=4)
        self.file_access_semaphore.release()

    def make_backup(self):
        backups_dir = os.path.join(gl.DATA_PATH, "pages", "backups")
        os.makedirs(backups_dir, exist_ok=True)

        src_path = self.json_path
        dst_path = os.path.join(backups_dir, os.path.basename(src_path))

        # Check if json in src is valid
        with open(src_path) as f:
            try:
                json.load(f)
            except json.decoder.JSONDecodeError as e:
                log.error(f"Invalid json in {src_path}: {e}")
                return

        shutil.copy2(src_path, dst_path)

        # Delete old backups
        backups_list = sorted(get_sub_folders(backups_dir))

        for folder in backups_list:
            # Keep at least 3 backups
            # new calculation on each iteration because a folder might have been deleted
            current_backup_count = len(get_sub_folders(backups_dir))
            if current_backup_count <= 3:
                break

            folder_path = os.path.join(backups_dir, folder)
            folder_mtime = datetime.fromtimestamp(os.path.getmtime(folder_path))

            if datetime.now() - folder_mtime > timedelta(weeks=1):
                shutil.rmtree(folder_path)
                log.debug(f"Deleted page backup: {folder_path}")

    def move_key_to_end(self, dictionary, key):
        if key in self.dict:
            value = self.dict.pop(key)
            self.dict[key] = value

    def set_background(self, file_path):
        self.dict.setdefault("background", {})
        self.dict["background"]["path"] = file_path
        self.save()

    def load_action_objects(self):
        new_action_objects = {}

        for input_type in Input.All:
            if len(self.deck_controller.inputs[input_type]) == 0:
                continue
            input_type = input_type.input_type
            for key in self.dict.get(input_type, {}):
                for state in self.dict[input_type][key].get("states", {}):
                    try:
                        state = int(state)
                    except ValueError:
                        continue
                    for i, action in enumerate(self.dict[input_type][key]["states"][str(state)].get("actions", [])):
                        if action.get("id") is None:
                            continue

                        input_ident = Input.FromTypeIdentifier(input_type, key)
                        # input_action_objects = input_ident.get_dict(new_action_objects)
                        # input_action_objects.setdefault(state, {})

                        action_object = self.get_new_action_object(
                            # loaded_action_objects=self.action_objects,
                            loaded_action_objects=self.action_objects,
                            action_id=action["id"],
                            state=state,
                            i=i,
                            input_ident=input_ident,
                        )
                        # input_action_objects[state][i] = action_object
                        new_action_objects.setdefault(input_type, {})
                        new_action_objects[input_type].setdefault(key, {})
                        new_action_objects[input_type][key].setdefault(state, {})
                        # new_action_objects[input_type][key][state].setdefault(i, {})
                        new_action_objects[input_type][key][state][i] = action_object

        old_actions = self.get_all_actions(self.action_objects)
        new_actions = self.get_all_actions(new_action_objects)

        for old_action in old_actions:
            if old_action not in new_actions:
                old_action.on_removed_from_cache()

        self.action_objects = new_action_objects

        self.call_actions_ready_and_set_flag()

    # def load_action_object_sector(self, loaded_action_objects, dict_key: str, state)

    def get_new_action_object(self, loaded_action_objects: dict, action_id: str, state: int, i: int, input_ident):
        
        action_holder = gl.plugin_manager.get_action_holder_from_id(action_id)

        ## No action holder found
        if action_holder is None:
            plugin_id = gl.plugin_manager.get_plugin_id_from_action_id(action_id)
            if gl.plugin_manager.get_is_plugin_out_of_date(plugin_id):
                return ActionOutdated(id=action_id, identifier=input_ident, state=state)
            return NoActionHolderFound(id=action_id, identifier=input_ident, state=state)

        ## Keep old object if it exists
        old_action = loaded_action_objects.get(input_ident.input_type, {}).get(input_ident.json_identifier, {}).get(state, {}).get(i)
        if old_action is not None:
            if isinstance(old_action, action_holder.action_base):
                return old_action #FIXME: gets never used
            
        ## Create new action object            
        action_object = action_holder.init_and_get_action(
            deck_controller=self.deck_controller,
            page=self,
            state=state,
            input_ident=input_ident,
        )
        return action_object

    def _load_action_objects(self):
        return
        # Store loaded action objects
        loaded_action_objects = copy(self.action_objects)

        add_threads: list[threading.Thread] = []

        # Load action objects
        self.action_objects = {}
        for input_type in Input.KeyTypes:
            for input_identifier in self.dict.get(input_type, {}):
                for state in self.dict[input_type][input_identifier].get("states", {}):
                    state = int(state)
                    input_ident = Input.FromTypeIdentifier(input_type, input_identifier)
                    if "actions" not in input_ident.get_config(self.dict)["states"][str(state)]:
                        continue
                    for i, action in enumerate(input_ident.get_config(self.dict)["states"][str(state)]["actions"]):
                        if action.get("id") is None:
                            continue

                        input_action_objects = input_ident.get_dict(self.action_objects)
                        input_action_objects.setdefault(state, {})

                        action_holder = gl.plugin_manager.get_action_holder_from_id(action["id"])
                        if action_holder is None:
                            plugin_id = gl.plugin_manager.get_plugin_id_from_action_id(action["id"])
                            if gl.plugin_manager.get_is_plugin_out_of_date(plugin_id):
                                input_action_objects[state][i] = ActionOutdated(id=action["id"])
                            else:
                                input_action_objects[state][i] = NoActionHolderFound(id=action["id"])
                            continue
                        action_class = action_holder.action_base
                        
                        if action_class is None:
                            input_action_objects[state][i] = NoActionHolderFound(id=action["id"])
                            continue

                        old_action_object = input_ident.get_dict(loaded_action_objects)
                        old_object = old_action_object.get(state, {}).get(i)
                        
                        if i in old_action_object.get(state, {}):
                            # if isinstance(loaded_action_objects.get(key, {}).get(i), action_class):
                            if old_object is not None:
                                if isinstance(old_object, action_class):
                                    input_action_objects[state][i] = old_action_object[state][i]
                                    continue

                        # action_object = action_holder.init_and_get_action(deck_controller=self.deck_controller, page=self, coords=key)
                        # self.action_objects[key][i] = action_object
                        if type == "keys" and self.deck_controller.coords_to_index(key.split("x")) > self.deck_controller.deck.key_count():
                            continue
                        thread = threading.Thread(target=self.add_action_object_from_holder, args=(action_holder, input_ident, state, i), name=f"add_action_object_from_holder_{input_ident.json_identifier}_{state}_{i}")
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

        all_old_objects: list[ActionBase] = []
        for type in loaded_action_objects:
            for key in loaded_action_objects[type]:
                for i in loaded_action_objects[type][key]:
                    all_old_objects.append(loaded_action_objects[type][key][i])

        all_action_objects: list[ActionBase] = []
        for type in self.action_objects:
            for key in self.action_objects[type]:
                for i in self.action_objects[type][key]:
                    all_action_objects.append(self.action_objects[type][key][i])

        for action in all_old_objects:
            if action not in all_action_objects:
                if isinstance(action, ActionBase):
                    action.on_removed_from_cache()
                    action.page = None
                del action

    def move_actions(self, type: str, from_key: str, to_key: str):
        from_actions = self.action_objects.get(type, {}).get(from_key, {})

        for action in from_actions.values():
            action: "ActionBase" = action
            if type == "keys":
                action.key_index = self.deck_controller.coords_to_index(to_key.split("x"))
            action.identifier = to_key

    def switch_actions_of_inputs(self, input_1: InputIdentifier, input_2: InputIdentifier):
        input_1_dict = self.action_objects.get(input_1.input_type, {}).get(input_1.json_identifier, {})
        input_2_dict = self.action_objects.get(input_2.input_type, {}).get(input_2.json_identifier, {})

        for state in input_1_dict:
            for action in input_1_dict[state].values():
                action.input_ident = input_2

        for state in input_2_dict:
            for action in input_2_dict[state].values():
                action.input_ident = input_1

        # Change in action_objects
        self.action_objects[input_1.input_type][input_1.json_identifier] = input_2_dict
        self.action_objects[input_2.input_type][input_2.json_identifier] = input_1_dict


    @log.catch
    def add_action_object_from_holder(self, action_holder: "ActionHolder", input_ident: "InputIdentifier", state: str, i: int):
        action_object = action_holder.init_and_get_action(deck_controller=self.deck_controller, page=self, input_ident=input_ident, state=state)
        if action_object is None:
            return
        self.action_objects.setdefault(input_ident.input_type, {})
        self.action_objects[input_ident.input_type].setdefault(input_ident.json_identifier, {})
        self.action_objects[input_ident.input_type][input_ident.json_identifier].setdefault(int(state), {})
        self.action_objects[input_ident.input_type][input_ident.json_identifier][int(state)][i] = action_object

    def remove_plugin_action_objects(self, plugin_id: str) -> bool:
        plugin_obj = gl.plugin_manager.get_plugin_by_id(plugin_id)
        if plugin_obj is None:
            return False
        for type in list(self.action_objects.keys()):
            for key in list(self.action_objects[type].keys()):
                for state in list(self.action_objects[type][key].keys()):
                    for index in list(self.action_objects[type][key].keys()):
                        if not isinstance(self.action_objects[type][key][state][index], ActionBase):
                            continue
                        if self.action_objects[type][key][state][index].plugin_base == plugin_obj:
                            # Remove object
                            action = self.action_objects[type][key][state][index]
                            del action

                            # Remove action from action_objects
                            del self.action_objects[type][key][state][index]

        return True
    
    def update_inputs_with_actions_from_plugin(self, plugin_id: str):
        # plugin_obj = gl.plugin_manager.get_plugin_by_id(plugin_id)
        for input_type in list(self.action_objects.keys()):
            for json_identifier in list(self.action_objects[input_type].keys()):
                for state in list(self.action_objects[input_type][json_identifier].keys()):
                    for index in list(self.action_objects[input_type][json_identifier][state].keys()):
                        action_base = self.action_objects[input_type][json_identifier][state][index]
                        action_id = action_base.action_id
                        print()

                        if gl.plugin_manager.get_plugin_id_from_action_id(action_id) == plugin_id:
                            identifier = Input.FromTypeIdentifier(input_type, json_identifier)

                            c_input = self.deck_controller.get_input(identifier)
                            if c_input.state == int(state):
                                c_input.update()
    
#    def get_keys_with_plugin(self, plugin_id: str):
#        plugin_obj = gl.plugin_manager.get_plugin_by_id(plugin_id)
#        if plugin_obj is None:
#            return []
#        
#        keys = []
#        for type in self.action_objects.values():
#            for key in self.action_objects[type]:
#                for state in self.action_objects[type][state]:
#                    for action in self.action_objects[type][state][key].values():
#                        if not isinstance(action, ActionBase):
#                            continue
#                        if action.plugin_base == plugin_obj:
#                            keys.append(key)
#
#        return keys

    def remove_plugin_actions_from_json(self, plugin_id: str):
        for type in Input.KeyTypes:
            for key in self.dict[type]:
                for state in self.dict[type][key].get("states", {}):
                    for i, action in enumerate(self.dict[type][key]["states"][state]["actions"]):
                        # Check if the action is from the plugin by using the plugin id before the action name
                        if action.id.split("::")[0] == plugin_id:
                            del self.dict[type][key]["states"][state]["actions"][i]

        self.save()

    def get_without_action_objects(self):
        dictionary = copy(self.dict)
        for type in Input.KeyTypes:
            for key in dictionary.get(type, {}):
                for state in dictionary[type][key].get("states", {}):
                    if "actions" not in dictionary[type][key]["states"][state]:
                        continue
                    for action in dictionary[type][key]["states"][state]["actions"]:
                        if "object" in action:
                            del action["object"]

        return dictionary

    def get_all_actions(self, action_dict: dict = None):
        if action_dict is None:
            action_dict = self.action_objects
        actions = []
        for input_type in action_dict:
            for key in action_dict[input_type]:
                for state in action_dict[input_type][key]:
                    for action in action_dict[input_type][key][state].values():
                        if action is None:
                            continue
                        if not isinstance(action, ActionBase):
                            continue
                        actions.append(action)
        return actions
    
    def get_all_actions_for_type(self, ident, only_action_bases: bool = False):
        actions = []
        input_type = ident.input_type
        input_identifier = ident.json_identifier
        if input_identifier in self.action_objects.get(input_type, {}):
            for state in self.action_objects[input_type].get(input_identifier, {}):
                for action in self.action_objects[input_type][input_identifier].get(state, {}).values():
                    if action is None or not action:
                        continue
                    if only_action_bases and not isinstance(action, ActionBase):
                        continue
                    actions.append(action)
        return actions
    
    def get_all_actions_for_input(self, ident, state, only_action_bases: bool = False):
        actions = []
        input_type = ident.input_type
        json_identifier = ident.json_identifier
        if json_identifier in self.action_objects.get(input_type, {}):
            if state in self.action_objects[input_type].get(json_identifier, {}):
                for action in self.action_objects[input_type][json_identifier].get(state, {}).values():
                    if action is None or not action:
                        continue
                    if only_action_bases and not isinstance(action, ActionBase):
                        continue
                    actions.append(action)
        return actions
    
    def get_action(self, identifier: InputIdentifier = None, state: int = None, index: int = None):
        return self.action_objects.get(identifier.input_type, {}).get(identifier.json_identifier, {}).get(state, {}).get(index)
    
    def get_action_dict(self, action_object = None, identifier: InputIdentifier = None, state: int = None, index: int = None):
        # Arg validation
        if action_object is None:
            if None in (identifier, state, index):
                raise ValueError("Please pass an identifier, state and index or an action object")
            
        if action_object is None:
            action_object = self.get_action(identifier, state, index)

        if action_object is None:
            raise ValueError("Could not find action object")
        
        for state in self.dict.get(action_object.input_ident.input_type, {}).get(action_object.input_ident.json_identifier, {}).get("states", {}):
            for i, action_dict in enumerate(self.dict[action_object.input_ident.input_type][action_object.input_ident.json_identifier]["states"][state].get("actions", [])):
                if self.action_objects.get(action_object.input_ident.input_type, {}).get(action_object.input_ident.json_identifier, {}).get(int(state), {}).get(i) is action_object:
                    return action_dict
                
        return {}
                
    def set_action_dict(self, action_object = None, identifier: InputIdentifier = None, state: int = None, index: int = None, action_dict: dict = None):
        # Arg validation
        if action_object is None:
            if None in (identifier, state, index):
                raise ValueError("Please pass an identifier, state and index or an action object")
            
        if action_object is None:
            action_object = self.get_action(identifier, state, index)

        if action_object is None:
            raise ValueError("Could not find action object")
        
        for state in self.dict.get(action_object.input_ident.input_type, {}).get(action_object.input_ident.json_identifier, {}).get("states", {}):
            for i, action_dict in enumerate(self.dict[action_object.input_ident.input_type][action_object.input_ident.json_identifier]["states"][state].get("actions", [])):
                if self.action_objects.get(action_object.input_ident.input_type, {}).get(action_object.input_ident.json_identifier, {}).get(int(state), {})[i] is action_object:
                    self.dict[action_object.input_ident.input_type][action_object.input_ident.json_identifier]["states"][state]["actions"][i] = action_dict
                    break

        self.save()
    
    def get_action_settings(self, action_object = None, identifier: InputIdentifier = None, state: int = None, index: int = None):
        action_dict = self.get_action_dict(action_object, identifier, state, index)
        return action_dict.get("settings", {})
        # Arg validation
        if action_object is None:
            if None in (identifier, state, index):
                raise ValueError("Please pass an identifier, state and index or an action object")
            
        if action_object is None:
            action_object = self.get_action(identifier, state, index)

        if action_object is None:
            raise ValueError("Could not find action object")

        for state in self.dict.get(action_object.input_ident.input_type, {}).get(action_object.input_ident.json_identifier, {}).get("states", {}):
            for i, action_dict in enumerate(self.dict[action_object.input_ident.input_type][action_object.input_ident.json_identifier]["states"][state].get("actions", [])):
                if self.action_objects.get(action_object.input_ident.input_type, {}).get(action_object.input_ident.json_identifier, {}).get(int(state), {})[i] is action_object:
                    return action_dict["settings"]
        return {}
    
    def set_action_settings(self, action_object = None, identifier: InputIdentifier = None, state: int = None, index: int = None, settings: dict = None):
        action_dict = self.get_action_dict(action_object, identifier, state, index)
        action_dict["settings"] = settings
        self.set_action_dict(action_object, identifier, state, index, action_dict)
        return
        # Arg validation
        if action_object is None:
            if None in (identifier, state, index):
                raise ValueError("Please pass an identifier, state and index or an action object")
            
        if action_object is None:
            action_object = self.get_action(identifier, state, index)

        if action_object is None:
            raise ValueError("Could not find action object")

        for state in self.dict.get(action_object.input_ident.input_type, {}).get(action_object.input_ident.json_identifier, {}).get("states", {}):
            for i, action_dict in enumerate(self.dict[action_object.input_ident.input_type][action_object.input_ident.json_identifier]["states"][state].get("actions", [])):
                if self.action_objects.get(action_object.input_ident.input_type, {}).get(action_object.input_ident.json_identifier, {}).get(int(state), {})[i] is action_object:
                    action_dict["settings"] = settings

        self.save()

    def get_action_event_assignments(self, action_object = None, identifier: InputIdentifier = None, state: int = None, index: int = None):
        action_dict = self.get_action_dict(action_object, identifier, state, index)
        return action_dict.get("event-assignments", {})
    
    def set_action_event_assignments(self, action_object = None, identifier: InputIdentifier = None, state: int = None, index: int = None, event_assignments: dict = None):
        action_dict = self.get_action_dict(action_object, identifier, state, index)
        action_dict["event-assignments"] = event_assignments
        self.set_action_dict(action_object, identifier, state, index, action_dict)


    def has_key_an_image_controlling_action(self, identifier, state: int):
        input_type = identifier.input_type
        json_identifier = identifier.json_identifier
        if input_type not in self.action_objects or json_identifier not in self.action_objects[input_type]:
            return False
        for action in self.action_objects[input_type][json_identifier][state].values():
            if hasattr(action, "CONTROLS_KEY_IMAGE"):
                if action.CONTROLS_KEY_IMAGE:
                    return True
        return False

    @log.catch
    def call_actions_ready_and_set_flag(self):
        for action in self.get_all_actions():
            if hasattr(action, "on_ready"):
                if not action.on_ready_called:
                    action.on_ready_called = True
                    action.on_ready()

    def clear_action_objects(self):
        for input_type in self.action_objects:
            for input_identifier in self.action_objects[input_type]:
                for state in self.action_objects[input_type][input_identifier]:
                    for i, action in enumerate(list(self.action_objects[input_type][input_identifier][state].values())):
                        self.action_objects[input_type][input_identifier][state][i].page = None
                        self.action_objects[input_type][input_identifier][state][i] = None
                        if isinstance(self.action_objects[input_type][input_identifier][state][i], ActionBase):
                            if hasattr(self.action_objects[input_type][input_identifier][state][i], "on_removed_from_cache"):
                                self.action_objects[input_type][input_identifier][state][i].on_removed_from_cache()
                        self.action_objects[input_type][input_identifier][state][i] = None
                        del self.action_objects[input_type][input_identifier][state][i]
            self.action_objects[input_type] = {}

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
    
    def reload_similar_pages(self, identifier: InputIdentifier = None, reload_self: bool = False,
                             load_brightness: bool = True, load_screensaver: bool = True, load_background: bool = True, load_inputs: bool = True,
                             load_dials: bool = True, load_touchscreens: bool = True):
        
        self.save()
        for page in self.get_pages_with_same_json(get_self=reload_self):
            page.load(load_from_file=True)
            # page.deck_controller.update_input(identifier)
            if identifier is not None:
                page.deck_controller.load_input_from_identifier(identifier, page)
            else:
                page.deck_controller.load_page(self)

    def get_action_comment(self, index: int, state: int, identifier: InputIdentifier) -> str:
        try:
            return self.dict[identifier.input_type][identifier.json_identifier]["states"][str(state)]["actions"][index].get("comment")
        except KeyError:
            return ""

    def set_action_comment(self, index: int, comment: str, state: int, identifier: InputIdentifier):
        if identifier.json_identifier in self.action_objects[identifier.input_type] and index in self.action_objects[identifier.input_type][identifier.json_identifier][state]:
            self.dict[identifier.input_type][identifier.json_identifier]["states"][str(state)]["actions"][index]["comment"] = comment
            self.save()

    def fix_action_objects_order(self, identifier: InputIdentifier) -> None:
        """
        #TODO: Switch to list instead of dict to avoid this
        """
        if identifier.json_identifier not in self.action_objects.get(identifier.input_type, {}):
            return
        
        actions = list(self.action_objects[identifier.input_type][identifier.json_identifier].values())

        self.action_objects[identifier.input_type][identifier.json_identifier] = {}
        for i, action in enumerate(actions):
            self.action_objects[identifier.input_type][identifier.json_identifier][i] = action
    
    # Configuration
    def _get_dict_value(self, keys: list[str]):
        value = self.dict
        for i, key in enumerate(keys):
            fallback = {}
            if i == len(keys) - 1:
                fallback = None

            try:
                value = value.get(key, fallback)
            except:
                return
        return value
    
    def _set_dict_value(self, keys: list[str], value):
        d = self.dict
        for i, key in enumerate(keys):
            if i == len(keys) - 1:
                d[key] = value
            else:
                d = d.setdefault(key, {})

        self.save()
        gl.page_manager.update_dict_of_pages_with_path(self.json_path)

    def update_key_image(self, coords: str | tuple[int, int], state: int) -> None:
        #TODO: Move to DeckController
        #TODO: Make input specific
        coords = self.get_tuple_coords(coords)
        for controller in gl.deck_manager.deck_controller:
            if controller.active_page.json_path != self.json_path:
                continue
            key_index = controller.coords_to_index(coords)
            if key_index is None:
                continue
            if key_index > len(controller.inputs[Input.Key]) - 1:
                continue
            key = controller.inputs[Input.Key][key_index]
            if key.state == state:
                key.update()

    def update_input(self, identifier: InputIdentifier, state: int, wake: bool = True) -> None:
        for controller in gl.deck_manager.deck_controller:
            if wake:
                if controller.screen_saver.showing:
                    controller.screen_saver.hide()

            if controller.active_page.json_path != self.json_path:
                continue
            c_input = controller.get_input(identifier)
            if c_input is None:
                continue
            if c_input.state != state:
                continue
            c_input.update()

    def get_controller_inputs(self, identifier: InputIdentifier) -> list["ControllerInput"]:
        inputs: list["ControllerInput"] = []

        for controller in gl.deck_manager.deck_controller:
            for c_input in controller.get_inputs(identifier):
                if c_input.identifier == identifier:
                    inputs.append(c_input)

        return inputs

    def get_controller_input_states(self, identifier: InputIdentifier, state: int) -> list["ControllerKeyState"]:
        matching_states: list["ControllerKeyState"] = []

        for controller_input in self.get_controller_inputs(identifier):
            for input_state in controller_input.states.values():
                if input_state.state == state:
                    matching_states.append(input_state)

        return matching_states

    def get_page_coords(self, coords: str | tuple[int, int]) -> str:
        if isinstance(coords, tuple):
            return f"{coords[0]}x{coords[1]}"
        return coords
    
    def get_tuple_coords(self, coords: str | tuple[int, int]) -> tuple[int, int]:
        if isinstance(coords, str):
            return tuple(map(int, coords.split("x")))
        return coords
    
    # Get/set methods

    def get_label_manager(self, identifier: InputIdentifier, state: int) -> "LabelManager":
        c_input = self.deck_controller.get_input(identifier)
        if c_input is None:
            return
        state = c_input.states.get(state)
        if state is None:
            return
        
        return state.label_manager
        

    def get_label_text(self, identifier: InputIdentifier, state: int, label_position: str) -> str:
        return self._get_dict_value([identifier.input_type, identifier.json_identifier, "states", str(state), "labels", label_position, "text"])

    def set_label_text(self, identifier: InputIdentifier, state: int, label_position: str, text: str, update: bool = True) -> None:
        for input_state in self.get_controller_input_states(identifier, state):
            input_state.label_manager.page_labels[label_position].text = text

        self._set_dict_value([identifier.input_type, identifier.json_identifier, "states", str(state), "labels", label_position, "text"], text)

        label_manager = self.get_label_manager(identifier, state)
        if label_manager is not None:
            label_manager.page_labels[label_position].text = text

        if update:
            self.update_input(identifier, state)

    def get_label_font_family(self, identifier: InputIdentifier, state: int, label_position: str) -> str:
        return self._get_dict_value([identifier.input_type, identifier.json_identifier, "states", str(state), "labels", label_position, "font-family"])

    def set_label_font_family(self, identifier: InputIdentifier, state: int, label_position: str, font_family: str, update: bool = True) -> None:
        for input_state in self.get_controller_input_states(identifier, state):
            input_state.label_manager.page_labels[label_position].font_family = font_family

        self._set_dict_value([identifier.input_type, identifier.json_identifier, "states", str(state), "labels", label_position, "font-family"], font_family)

        label_manager = self.get_label_manager(identifier, state)
        if label_manager is not None:
            label_manager.page_labels[label_position].font_name = font_family
            label_manager.update_label_editor()

        if update:
            self.update_input(identifier, state)

    def get_label_font_size(self, identifier: InputIdentifier, state: int, label_position: str) -> int:
        return self._get_dict_value([identifier.input_type, identifier.json_identifier, "states", str(state), "labels", label_position, "font-size"])
    
    def get_label_font_style(self, identifier: InputIdentifier, state: int, label_position: str) -> int:
        return self._get_dict_value([identifier.input_type, identifier.json_identifier, "states", str(state), "labels", label_position, "font-style"])
    
    def get_label_font_weight(self, identifier: InputIdentifier, state: int, label_position: str) -> int:
        return self._get_dict_value([identifier.input_type, identifier.json_identifier, "states", str(state), "labels", label_position, "font-weight"])

    def set_label_font_size(self, identifier: InputIdentifier, state: int, label_position: str, font_size: int, update: bool = True) -> None:
        for key_state in self.get_controller_input_states(identifier, state):
            key_state.label_manager.page_labels[label_position].font_size = font_size

        self._set_dict_value([identifier.input_type, identifier.json_identifier, "states", str(state), "labels", label_position, "font-size"], font_size)

        label_manager = self.get_label_manager(identifier, state)
        if label_manager is not None:
            label_manager.page_labels[label_position].font_size = font_size
            label_manager.update_label_editor()

        if update:
            self.update_input(identifier, state)

    def set_label_font_weight(self, identifier: InputIdentifier, state: int, label_position: str, font_weight: int, update: bool = True) -> None:
        for key_state in self.get_controller_input_states(identifier, state):
            key_state.label_manager.page_labels[label_position].font_weight = font_weight

        self._set_dict_value([identifier.input_type, identifier.json_identifier, "states", str(state), "labels", label_position, "font-weight"], font_weight)

        label_manager = self.get_label_manager(identifier, state)
        if label_manager is not None:
            label_manager.page_labels[label_position].font_weight = font_weight
            label_manager.update_label_editor()

        if update:
            self.update_input(identifier, state)

    def set_label_font_color(self, identifier: InputIdentifier, state: int, label_position: str, font_color: list[int], update: bool = True) -> None:
        for key_state in self.get_controller_input_states(identifier, state):
            key_state.label_manager.page_labels[label_position].color = font_color

        self._set_dict_value([identifier.input_type, identifier.json_identifier, "states", str(state), "labels", label_position, "color"], font_color)

        label_manager = self.get_label_manager(identifier, state)
        if label_manager is not None:
            label_manager.page_labels[label_position].color = font_color
            label_manager.update_label_editor()

        if update:
            self.update_input(identifier, state)

    def set_label_outline_width(self, identifier: InputIdentifier, state: int, label_position: str, outline_width: list[int], update: bool = True) -> None:
        for key_state in self.get_controller_input_states(identifier, state):
            key_state.label_manager.page_labels[label_position].outline_width = outline_width

        self._set_dict_value([identifier.input_type, identifier.json_identifier, "states", str(state), "labels", label_position, "outline_width"], outline_width)

        label_manager = self.get_label_manager(identifier, state)
        if label_manager is not None:
            label_manager.page_labels[label_position].outline_width = outline_width
            label_manager.update_label_editor()

        if update:
            self.update_input(identifier, state)

    def set_label_outline_color(self, identifier: InputIdentifier, state: int, label_position: str, outline_color: list[int], update: bool = True) -> None:
        for key_state in self.get_controller_input_states(identifier, state):
            key_state.label_manager.page_labels[label_position].outline_color = outline_color

        self._set_dict_value([identifier.input_type, identifier.json_identifier, "states", str(state), "labels", label_position, "outline_color"], outline_color)

        label_manager = self.get_label_manager(identifier, state)
        if label_manager is not None:
            label_manager.page_labels[label_position].outline_color = outline_color
            label_manager.update_label_editor()

        if update:
            self.update_input(identifier, state)

    def set_label_font_style(self, identifier: InputIdentifier, state: int, label_position: str, font_style: str, update: bool = True) -> None:
        for key_state in self.get_controller_input_states(identifier, state):
            key_state.label_manager.page_labels[label_position].style = font_style

        self._set_dict_value([identifier.input_type, identifier.json_identifier, "states", str(state), "labels", label_position, "style"], font_style)

        label_manager = self.get_label_manager(identifier, state)
        if label_manager is not None:
            label_manager.page_labels[label_position].style = font_style
            label_manager.update_label_editor()

        if update:
            self.update_input(identifier, state)

    def get_media_size(self, identifier: InputIdentifier, state: int) -> float:
        return self._get_dict_value([identifier.input_type, identifier.json_identifier, "states", str(state), "media", "size"])

    def set_media_size(self, identifier: InputIdentifier, state: int, size: float, update: bool = True) -> None:
        for key_state in self.get_controller_input_states(identifier, state):
            key_state.layout_manager.page_layout.size = size

        self._set_dict_value([identifier.input_type, identifier.json_identifier, "states", str(state), "media", "size"], size)

        if update:
            self.update_input(identifier, state)

    def get_media_valign(self, identifier: InputIdentifier, state: int) -> str:
        return self._get_dict_value([identifier.input_type, identifier.json_identifier, "states", str(state), "media", "valign"])

    def set_media_valign(self, identifier: InputIdentifier, state: int, valign: str, update: bool = True) -> None:
        for key_state in self.get_controller_input_states(identifier, state):
            key_state.layout_manager.page_layout.valign = valign

        self._set_dict_value([identifier.input_type, identifier.json_identifier, "states", str(state), "media", "valign"], valign)

        if update:
            self.update_input(identifier, state)

    def get_media_halign(self, identifier: InputIdentifier, state: int) -> str:
        return self._get_dict_value([identifier.input_type, identifier.json_identifier, "states", str(state), "media", "halign"])

    def set_media_halign(self, identifier: InputIdentifier, state: int, halign: str, update: bool = True) -> None:
        for key_state in self.get_controller_input_states(identifier, state):
            key_state.layout_manager.page_layout.halign = halign

        self._set_dict_value([identifier.input_type, identifier.json_identifier, "states", str(state), "media", "halign"], halign)

        if update:
            self.update_input(identifier, state)

    def get_media_path(self, identifier: InputIdentifier, state: int) -> str:
        return self._get_dict_value([identifier.input_type, identifier.json_identifier, "states", str(state), "media", "path"])

    def set_media_path(self, identifier: InputIdentifier, state: int, path: str, update: bool = True) -> None:
        for key_state in self.get_controller_input_states(identifier, state):
            key_state.layout_manager.page_layout.path = path

        self._set_dict_value([identifier.input_type, identifier.json_identifier, "states", str(state), "media", "path"], path)

        if update:
            self.update_input(identifier, state)

    def get_background_color(self, identifier: InputIdentifier, state: int) -> list[int]:
        return self._get_dict_value([identifier.input_type, identifier.json_identifier, "states", str(state), "background", "color"])

    def set_background_color(self, identifier: InputIdentifier, state: int, color: list[int], update: bool = True) -> None:
        for key_state in self.get_controller_input_states(identifier, state):
            key_state.background_color = color

        self._set_dict_value([identifier.input_type, identifier.json_identifier, "states", str(state), "background", "color"], color)

        if update:
            self.update_input(identifier, state)


def get_sub_folders(parent: str) -> List[str]:
    if not os.path.isdir(parent):
        return []

    return [folder for folder in os.listdir(parent) if os.path.isdir(os.path.join(parent, folder))]


class NoActionHolderFound:
    def __init__(self, id: str, state: int, identifier: InputIdentifier = None):
        self.id = id
        self.action_id = id
        self.type = type
        self.identifier = identifier
        self.state = state


class ActionOutdated:
    def __init__(self, id: str, state: int, identifier: InputIdentifier = None):
        self.id = id
        self.action_id = id
        self.type = type
        self.identifier = identifier
        self.state = state