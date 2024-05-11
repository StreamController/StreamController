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
from loguru import logger as log
from copy import copy
import shutil

# Import globals
import globals as gl

from src.backend.PluginManager.ActionBase import ActionBase
# Import typing
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from src.backend.PluginManager.ActionHolder import ActionHolder
    from src.backend.DeckManagement.DeckController import ControllerKeyState, ControllerKey

class Page:
    def __init__(self, json_path, deck_controller, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.dict = {}

        self.json_path = json_path
        self.deck_controller = deck_controller

        # Dir that contains all actions this allows us to keep them at reload
        self.action_objects = {}

        self.ready_to_clear = True

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
        loaded_action_objects = copy(self.action_objects)

        add_threads: list[threading.Thread] = []

        # Load action objects
        self.action_objects = {}
        for key in self.dict.get("keys", {}):
            for state in self.dict["keys"][key].get("states", {}):
                state = int(state)
                if "actions" not in self.dict["keys"][key]["states"][str(state)]:
                    continue
                for i, action in enumerate(self.dict["keys"][key]["states"][str(state)]["actions"]):
                    if action.get("id") is None:
                        continue

                    self.action_objects.setdefault(key, {})
                    self.action_objects[key].setdefault(state, {})

                    action_holder = gl.plugin_manager.get_action_holder_from_id(action["id"])
                    if action_holder is None:
                        plugin_id = gl.plugin_manager.get_plugin_id_from_action_id(action["id"])
                        if gl.plugin_manager.get_is_plugin_out_of_date(plugin_id):
                            self.action_objects[key][state][i] = ActionOutdated(id=action["id"])
                        else:
                            self.action_objects[key][state][i] = NoActionHolderFound(id=action["id"])
                        continue
                    action_class = action_holder.action_base
                    
                    if action_class is None:
                        self.action_objects[key][state][i] = NoActionHolderFound(id=action["id"])
                        continue

                    old_object = loaded_action_objects.get(key, {}).get(state, {}).get(i)
                    
                    if i in loaded_action_objects.get(key, {}).get(state, {}):
                        # if isinstance(loaded_action_objects.get(key, {}).get(i), action_class):
                        if old_object is not None:
                            if isinstance(old_object, action_class):
                                self.action_objects[key][state][i] = loaded_action_objects[key][state][i]
                                continue

                    # action_object = action_holder.init_and_get_action(deck_controller=self.deck_controller, page=self, coords=key)
                    # self.action_objects[key][i] = action_object
                    if self.deck_controller.coords_to_index(key.split("x")) > self.deck_controller.deck.key_count():
                        continue
                    thread = threading.Thread(target=self.add_action_object_from_holder, args=(action_holder, key, state, i), name=f"add_action_object_from_holder_{key}_{state}_{i}")
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
        for key in loaded_action_objects:
            for i in loaded_action_objects[key]:
                all_old_objects.append(loaded_action_objects[key][i])

        all_action_objects: list[ActionBase] = []
        for key in self.action_objects:
            for i in self.action_objects[key]:
                all_action_objects.append(self.action_objects[key][i])

        for action in all_old_objects:
            if action not in all_action_objects:
                if isinstance(action, ActionBase):
                    action.on_removed_from_cache()
                    action.page = None
                del action

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


    @log.catch
    def add_action_object_from_holder(self, action_holder: "ActionHolder", key: str, state: str, i: int):
        action_object = action_holder.init_and_get_action(deck_controller=self.deck_controller, page=self, coords=key, state=state)
        if action_object is None:
            return
        self.action_objects.setdefault(key, {})
        self.action_objects[key].setdefault(int(state), {})
        self.action_objects[key][int(state)][i] = action_object

    def remove_plugin_action_objects(self, plugin_id: str) -> bool:
        plugin_obj = gl.plugin_manager.get_plugin_by_id(plugin_id)
        if plugin_obj is None:
            return False
        for key in list(self.action_objects.keys()):
            for index in list(self.action_objects[key].keys()):
                if not isinstance(self.action_objects[key][index], ActionBase):
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
                if not isinstance(action, ActionBase):
                    continue
                if action.plugin_base == plugin_obj:
                    keys.append(key)

        return keys

    def remove_plugin_actions_from_json(self, plugin_id: str): 
        for key in self.dict["keys"]:
            for state in self.dict["keys"][key].get("states", {}):
                for i, action in enumerate(self.dict["keys"][key]["states"][state]["actions"]):
                    # Check if the action is from the plugin by using the plugin id before the action name
                    if self.dict["keys"][key]["states"][state]["actions"].split("::")[0] == plugin_id:
                        del self.dict["keys"][key]["states"][state]["actions"][i]

        self.save()

    def get_without_action_objects(self):
        dictionary = copy(self.dict)
        for key in dictionary.get("keys", {}):
            for state in dictionary["keys"][key].get("states", {}):
                if "actions" not in dictionary["keys"][key]["states"][state]:
                    continue
                for action in dictionary["keys"][key]["states"][state]["actions"]:
                    if "object" in action:
                        del action["object"]

        return dictionary

    def get_all_actions(self):
        actions = []
        for key in self.action_objects:
            for state in self.action_objects[key]:
                for action in self.action_objects[key][state].values():
                    if action is None:
                        continue
                    if not isinstance(action, ActionBase):
                        continue
                    actions.append(action)
        return actions
    
    def get_all_actions_for_key(self, key, only_action_bases: bool = False):
        actions = []
        if key in self.action_objects:
            for state in self.action_objects[key]:
                for action in self.action_objects[key][state].values():
                    if action is None:
                        continue
                    if only_action_bases and not isinstance(action, ActionBase):
                        continue
                    actions.append(action)
        return actions
    
    def get_all_actions_for_key_and_state(self, key, state, only_action_bases: bool = False):
        actions = []
        if key in self.action_objects:
            if state in self.action_objects[key]:
                for action in self.action_objects[key][state].values():
                    if action is None:
                        continue
                    if only_action_bases and not isinstance(action, ActionBase):
                        continue
                    actions.append(action)
        return actions
    
    def get_settings_for_action(self, action_object, coords: list = None, state: int = None):
        if coords is None or state is None:
            for key in self.dict["keys"]:
                for state in self.dict["keys"][key].get("states", {}):
                    for i, action in enumerate(self.dict["keys"][key]["states"][state]["actions"]):
                        if not key in self.action_objects:
                            break
                        if not i in self.action_objects[key]:
                            break
                        if self.action_objects[key][int(state)][i] == action_object:
                            return action["settings"]
        else:
            for state in self.dict["keys"][coords].get("states", {}):
                for i, action in enumerate(self.dict["keys"][coords]["states"][state].get("actions", [])):
                    if not coords in self.action_objects:
                        break
                    if int(state) not in self.action_objects[coords]:
                        break
                    if not i in self.action_objects[coords][int(state)]:
                        break
                    if self.action_objects[coords][int(state)][i] == action_object:
                        return action["settings"]
        return {}
                
    def set_settings_for_action(self, action_object, settings: dict, coords: list = None, state: int = None):
        if coords is None or state is None and action_object:
            coords = action_object.page_coords
            state = action_object.state

        for state in self.dict["keys"][coords].get("states", {}):
            for i, action in enumerate(self.dict["keys"][coords]["states"][state].get("actions", [])):
                self.action_objects.setdefault(coords, {})
                if self.action_objects[coords].get(int(state), {}).get(i) == action_object:
                    self.dict["keys"][coords]["states"][state]["actions"][i]["settings"] = settings

    def has_key_an_image_controlling_action(self, page_coords: str, state: int):
        if page_coords not in self.action_objects:
            return False
        for action in self.action_objects[page_coords][state].values():
            if hasattr(action, "CONTROLS_KEY_IMAGE"):
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
                if isinstance(self.action_objects[key][i], ActionBase):
                    if hasattr(self.action_objects[key][i], "on_removed_from_cache"):
                        self.action_objects[key][i].on_removed_from_cache()
                self.action_objects[key][i] = None
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

    def get_action_comment(self, page_coords: str, index: int, state: int):
        if page_coords in self.action_objects:
            if index in self.action_objects[page_coords]:
                try:
                    return self.dict["keys"][page_coords]["states"][str(state)]["actions"][index].get("comment")
                except:
                    return ""
            
    def set_action_comment(self, page_coords: str, index: int, comment: str, state: int):
        if page_coords in self.action_objects:
            if index in self.action_objects[page_coords]:
                self.dict["keys"][page_coords]["states"][str(state)]["actions"][index]["comment"] = comment
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
    
    def _set_dict_value(self, keys: list[str], value, coords: str | tuple[int, int] = None, state: int = None):
        d = self.dict
        for i, key in enumerate(keys):
            if i == len(keys) - 1:
                d[key] = value
            else:
                d = d.setdefault(key, {})

        self.save()
        gl.page_manager.update_dict_of_pages_with_path(self.json_path)

    def update_key_image(self, coords: str | tuple[int, int], state: int) -> None:
        coords = self.get_tuple_coords(coords)
        for controller in gl.deck_manager.deck_controller:
            if controller.active_page.json_path != self.json_path:
                continue
            key_index = controller.coords_to_index(coords)
            if key_index is None:
                continue
            if key_index > len(controller.keys) - 1:
                continue
            key = controller.keys[key_index]
            if key.state == state:
                key.update()

    def get_controller_keys(self, coords: str | tuple[int, int]) -> list["ControllerKey"]:
        coords = self.get_tuple_coords(coords)

        keys: list["ControllerKey"] = []
        for controller in gl.deck_manager.deck_controller:
            if controller.active_page.json_path != self.json_path:
                continue
            key_index = controller.coords_to_index(coords)
            if key_index is None:
                continue
            if key_index > len(controller.keys) - 1:
                continue
            keys.append(controller.keys[key_index])

        return keys


    def get_controller_key_states(self, coords: str | tuple[int, int], state: int) -> list["ControllerKeyState"]:
        matching_states: list["ControllerKeyState"] = []

        for key in self.get_controller_keys(coords):
            for key_state in key.states.values():
                if key_state.state == state:
                    matching_states.append(key_state)

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

    def get_label_text(self, coords: str | tuple[int, int], state: int, label_position: str) -> str:
        coords = self.get_page_coords(coords)
        return self._get_dict_value(["keys", coords, "states", str(state), "labels", label_position, "text"])
    
    def set_label_text(self, coords: str | tuple[int, int], state: int, label_position: str, text: str, update: bool = True) -> None:
        coords = self.get_page_coords(coords)
        for key_state in self.get_controller_key_states(coords, state):
            key_state.label_manager.page_labels[label_position].text = text

        self._set_dict_value(["keys", coords, "states", str(state), "labels", label_position, "text"], text, coords, state)

        if update:
            self.update_key_image(coords, state)

    def get_label_font_family(self, coords: str | tuple[int, int], state: int, label_position: str) -> str:
        coords = self.get_page_coords(coords)
        return self._get_dict_value(["keys", coords, "states", str(state), "labels", label_position, "font-family"])
    
    def set_label_font_family(self, coords: str | tuple[int, int], state: int, label_position: str, font_family: str, update: bool = True) -> None:
        coords = self.get_page_coords(coords)
        for key_state in self.get_controller_key_states(coords, state):
            key_state.label_manager.page_labels[label_position].font_family = font_family

        self._set_dict_value(["keys", coords, "states", str(state), "labels", label_position, "font-family"], font_family, coords, state)

        if update:
            self.update_key_image(coords, state)

    def get_label_font_size(self, coords: str | tuple[int, int], state: int, label_position: str) -> int:
        coords = self.get_page_coords(coords)
        return self._get_dict_value(["keys", coords, "states", str(state), "labels", label_position, "font-size"])
    
    def set_label_font_size(self, coords: str | tuple[int, int], state: int, label_position: str, font_size: int, update: bool = True) -> None:
        coords = self.get_page_coords(coords)
        for key_state in self.get_controller_key_states(coords, state):
            key_state.label_manager.page_labels[label_position].font_size = font_size

        self._set_dict_value(["keys", coords, "states", str(state), "labels", label_position, "font-size"], font_size, coords, state)

        if update:
            self.update_key_image(coords, state)

    def get_label_font_color(self, coords: str | tuple[int, int], state: int, label_position: str) -> list[int]:
        coords = self.get_page_coords(coords)
        return self._get_dict_value(["keys", coords, "states", str(state), "labels", label_position, "color"])
    
    def set_label_font_color(self, coords: str | tuple[int, int], state: int, label_position: str, font_color: list[int], update: bool = True) -> None:
        coords = self.get_page_coords(coords)
        for key_state in self.get_controller_key_states(coords, state):
            key_state.label_manager.page_labels[label_position].color = font_color

        self._set_dict_value(["keys", coords, "states", str(state), "labels", label_position, "color"], font_color, coords, state)

        if update:
            self.update_key_image(coords, state)

    def get_media_size(self, coords: str | tuple[int, int], state: int) -> float:
        coords = self.get_page_coords(coords)
        return self._get_dict_value(["keys", coords, "states", str(state), "media", "size"])
    
    def set_media_size(self, coords: str | tuple[int, int], state: int, size: float, update: bool = True) -> None:
        coords = self.get_page_coords(coords)
        for key_state in self.get_controller_key_states(coords, state):
            key_state.layout_manager.media_size = size

        self._set_dict_value(["keys", coords, "states", str(state), "media", "size"], size, coords, state)

        if update:
            self.update_key_image(coords, state)

    def get_media_valign(self, coords: str | tuple[int, int], state: int) -> str:
        coords = self.get_page_coords(coords)
        return self._get_dict_value(["keys", coords, "states", str(state), "media", "valign"])

    def set_media_valign(self, coords: str | tuple[int, int], state: int, valign: str, update: bool = True) -> None:
        coords = self.get_page_coords(coords)
        for key_state in self.get_controller_key_states(coords, state):
            key_state.layout_manager.valign = valign

        self._set_dict_value(["keys", coords, "states", str(state), "media", "valign"], valign, coords, state)

        if update:
            self.update_key_image(coords, state)

    def get_media_halign(self, coords: str | tuple[int, int], state: int) -> str:
        coords = self.get_page_coords(coords)
        return self._get_dict_value(["keys", coords, "states", str(state), "media", "halign"])

    def set_media_halign(self, coords: str | tuple[int, int], state: int, halign: str, update: bool = True) -> None:
        coords = self.get_page_coords(coords)
        for key_state in self.get_controller_key_states(coords, state):
            key_state.layout_manager.halign = halign

        self._set_dict_value(["keys", coords, "states", str(state), "media", "halign"], halign, coords, state)

        if update:
            self.update_key_image(coords, state)

    def get_background_color(self, coords: str | tuple[int, int], state: int) -> list[int]:
        coords = self.get_page_coords(coords)
        return self._get_dict_value(["keys", coords, "states", str(state), "background", "color"])
    
    def set_background_color(self, coords: str | tuple[int, int], state: int, color: list[int], update: bool = True) -> None:
        coords = self.get_page_coords(coords)

        for key_state in self.get_controller_key_states(coords, state):
            key_state.background_color = color

        self._set_dict_value(["keys", coords, "states", str(state), "background", "color"], color, coords, state)

        if update:
            self.update_key_image(coords, state)


class NoActionHolderFound:
    def __init__(self, id: str):
        self.id = id

class ActionOutdated:
    def __init__(self, id: str):
        self.id = id