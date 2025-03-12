"""
Author: Core447
Year: 2024

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
any later version.

This programm comes with ABSOLUTELY NO WARRANTY!

You should have received a copy of the GNU General Public License
along with this program. If not, see <https://www.gnu.org/licenses/>.
"""

from concurrent.futures import thread
import threading
from typing import TYPE_CHECKING

from src.backend.PluginManager import ActionCore
if TYPE_CHECKING:
    from src.backend.DeckManagement.DeckController import ControllerInputState

class ActionPermissionManager:
    def __init__(self, controller_input_state: "ControllerInputState"):
        self.controller_input_state = controller_input_state
        self.input_identifier = controller_input_state.controller_input.identifier
        self.deck_controller = controller_input_state.deck_controller

    ## Labels
    def get_label_control_indices(self) -> list[int | None]:
        state_dict = self.get_state_dict()
        return state_dict.get("label-control-actions", [None, None, None])
    
    def get_label_control_index(self, label_position: int) -> ActionCore:
        return self.get_label_control_indices()[label_position]
    
    def set_label_control_index(self, label_position: int, index: int, reload_pages: bool = True, reload_self: bool = True):
        state_dict = self.get_state_dict()
        state_dict.setdefault("label-control-actions", [None, None, None])
        state_dict["label-control-actions"][label_position] = index
        self.set_state_dict(state_dict)

        self.reload_pages(reload_pages, reload_self)

    ## Media
    def get_image_control_index(self) -> ActionCore:
        state_dict = self.get_state_dict()
        return state_dict.get("image-control-action", None)
    
    def set_image_control_index(self, index: int, reload_pages: bool = True, reload_self: bool = True):
        state_dict = self.get_state_dict()
        state_dict["image-control-action"] = index
        self.set_state_dict(state_dict)

        self.reload_pages(reload_pages, reload_self)

    ## Background
    def get_background_control_index(self) -> ActionCore:
        state_dict = self.get_state_dict()
        return state_dict.get("background-control-action", None)
    
    def set_background_control_index(self, index: int, reload_pages: bool = True, reload_self: bool = True):
        state_dict = self.get_state_dict()
        state_dict["background-control-action"] = index
        self.set_state_dict(state_dict)

        self.reload_pages(reload_pages, reload_self)

    ## Input dict
    def get_input_dict(self) -> dict:
        return self.input_identifier.get_dict(self.deck_controller.active_page.dict)
    
    def set_input_dict(self, new_input_dict: dict):
        new_input_dict = new_input_dict.copy() # In case it's a reference to the original
        input_dict = self.get_input_dict()
        input_dict.clear()
        input_dict.update(new_input_dict)
        self.deck_controller.active_page.save()

    ## State dict
    def get_state_dict(self) -> dict:
        return self.get_input_dict().get("states", {}).get(str(self.controller_input_state.state), {})

    def set_state_dict(self, new_state_dict: dict):
        new_state_dict = new_state_dict.copy() # In case it's a reference to the original
        state_dict = self.get_state_dict()
        state_dict.clear()
        state_dict.update(new_state_dict)
        self.deck_controller.active_page.save()

    ## Helper

    def reload_pages(self, reload_pages: bool = True, reload_self: bool = True) -> None:
        if reload_pages:
            threading.Thread(target=self.deck_controller.active_page.reload_similar_pages, kwargs={"identifier":self.input_identifier, "reload_self":reload_self}).start()