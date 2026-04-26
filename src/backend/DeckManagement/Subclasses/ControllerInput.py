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
import threading
from threading import Timer
from typing import TYPE_CHECKING

from PIL import Image
from gi.repository import GLib
from loguru import logger as log

from src.backend.DeckManagement.HelperMethods import recursive_hasattr
from src.backend.DeckManagement.InputIdentifier import InputEvent, InputIdentifier
from src.backend.DeckManagement.Subclasses.ActionPermissionManager import ActionPermissionManager
from src.backend.DeckManagement.Subclasses.InputStateManagers import (
    BackgroundManager,
    LabelManager,
    LayoutManager,
)
from src.backend.PageManagement.Page import ActionOutdated, NoActionHolderFound, Page
from src.backend.PluginManager.ActionCore import ActionCore
from src.Signals import Signals

import globals as gl

if TYPE_CHECKING:
    from src.backend.DeckManagement.DeckController import DeckController, ControllerKeyState


class ControllerInputState:
    def __init__(self, controller_input: "ControllerInput", state: int):
        self.controller_input = controller_input
        self.deck_controller = controller_input.deck_controller
        self.state = state
        self._overlay: Image.Image = None
        self.hide_overlay_timer: Timer = None

        # managers
        self.layout_manager = LayoutManager(self.controller_input)
        self.label_manager = LabelManager(self.controller_input)
        self.background_manager = BackgroundManager(self.controller_input)

        self.action_permission_manager = ActionPermissionManager(self)

    def __int__(self):
        return self.state
    
    def ready(self):
        pass

    def stop_overlay_timer(self):
        if self.hide_overlay_timer is not None:
            self.hide_overlay_timer.cancel()
            self.hide_overlay_timer = None

    def show_overlay(self, image: Image.Image, duration: int = -1):
        """
        duration: -1 for infinite
        """
        if duration == 0:
            self.stop_overlay_timer()
            self._overlay = None
            self.update()
        elif duration > 0:
            self._overlay = image
            self.update()
            self.hide_overlay_timer = Timer(duration, self.hide_error)
            self.hide_overlay_timer.start()
        else:
            self._overlay = image
            self.update()

    def hide_overlay(self):
        self._overlay = False
        self.update()

    def show_error(self, duration: int = -1):
        error_img = Image.open(os.path.join("Assets", "images", "error.png"))
        self.show_overlay(error_img, duration=duration)

    def hide_error(self):
        self.hide_overlay()

    def close_resources(self) -> None:
        pass

    def get_own_actions(self) -> list["ActionCore"]:
        if not self.deck_controller.get_alive(): return []
        active_page = self.deck_controller.active_page
        active_page = self.controller_input.deck_controller.active_page
        if active_page is None:
            return []
        if active_page.action_objects is None:
            return []
        actions = self.deck_controller.active_page.get_all_actions_for_input(self.controller_input.identifier, self.state)

        return actions

    def update(self) -> None:
        if self.controller_input.state == self.state:
            self.controller_input.update()
    
    def own_actions_update(self) -> None:
        for action in self.get_own_actions():
            if not isinstance(action, ActionCore):
                continue
            if not action.on_ready_called:
                continue
            action.on_update()

    @log.catch
    def own_actions_tick(self) -> None:
        for action in self.get_own_actions():
            if not isinstance(action, ActionCore):
                continue
            if not action.on_ready_called:
                continue
            action.on_tick()

    @log.catch
    def own_actions_event_callback(self, event: InputEvent, data: dict = None, show_notifications: bool = False) -> None:
        for action in self.get_own_actions():
            if isinstance(action, ActionOutdated):
                if show_notifications:
                    plugin_id = gl.plugin_manager.get_plugin_id_from_action_id(action.id)
                    gl.app.send_outdated_plugin_notification(plugin_id)
                continue
            if isinstance(action, NoActionHolderFound):
                if show_notifications:
                    plugin_id = gl.plugin_manager.get_plugin_id_from_action_id(action.id)
                    gl.app.send_missing_plugin_notification(plugin_id)
                continue

            # parsed_event = event
            # if action.allow_event_configuration:
                # parsed_event = action.event_manager.get_event_assigner_for_event(event)

            if event is None:
                continue

            if not isinstance(action, ActionCore):
                continue

            action._raw_event_callback(event, data)

    def own_actions_ready_threaded(self) -> None:
        threading.Thread(target=self.own_actions_ready, name="own_actions_ready").start()

    def own_actions_update_threaded(self) -> None:
        threading.Thread(target=self.own_actions_update, name="own_actions_update").start()

    def own_actions_tick_threaded(self) -> None:
        threading.Thread(target=self.own_actions_tick, name="own_actions_tick").start()

    def own_actions_event_callback_threaded(self, event: InputEvent, data: dict = None, show_notifications: bool = False) -> None:
        threading.Thread(target=self.own_actions_event_callback, args=(event, data, show_notifications), name="own_actions_event_callback").start()

    def remove_media(self) -> None:
        page = self.controller_input.deck_controller.active_page
        if page is None:
            return

        page.set_media_path(identifier=self.controller_input.identifier, state=self.state, path=None)

        self.update()


class ControllerInput:
    def __init__(self, deck_controller: "DeckController", state_class: ControllerInputState, identifier: InputIdentifier):
        self.deck_controller = deck_controller
        self.state = 0
        self.hide_error_timer: Timer = None
        self.hold_start_timer: Timer = None
        self.ControllerStateClass = state_class
        self.identifier: InputIdentifier = identifier
        self.media_ticks: int = 0

        self.is_visual: bool = True

        self.enable_states: bool = True

        self.states: dict[int, ControllerInputState] = {
            0: self.ControllerStateClass(self, 0),
        }

        self.states[self.state].ready()

    @staticmethod
    def Available_Identifiers(deck):
        raise AttributeError

    def update(self) -> None:
        pass

    def event_callback(self) -> None:
        pass

    def start_hold_timer(self):
        self.stop_hold_timer()

        self.hold_start_timer = threading.Timer(self.deck_controller.hold_time, self.on_hold_timer_end)
        self.hold_start_timer.setDaemon(True)
        self.hold_start_timer.setName("HoldTimer")
        self.hold_start_timer.start()

    def stop_hold_timer(self):
        if self.hold_start_timer is None:
            return
        
        self.hold_start_timer.cancel()
        self.hold_start_timer = None

    def create_n_states(self, n: int):
        if not self.enable_states:
            n = 1

        for state in self.states.values():
            state.close_resources()
        self.states.clear()

        for i in range(n):
            self.states[i] = self.ControllerStateClass(self, i)

    def load_from_page(self, page: Page):
        input_dict = self.identifier.get_config(page)
        self.load_from_input_dict(input_dict)

    def load_from_input_dict(self, page_dict, update: bool = True):
        pass

    def add_new_state(self, switch: bool = True):
        if not self.enable_states:
            if len(self.states) >= 1:
                return
            
        d = self.identifier.get_config(self.deck_controller.active_page)

        # Add new state
        self.states[len(self.states)] = self.ControllerStateClass(self, len(self.states))
        # Write to json
        for state in self.states.keys():
            d["states"].setdefault(str(state), {})

        self.deck_controller.active_page.save()
        gl.page_manager.update_dict_of_pages_with_path(self.deck_controller.active_page.json_path)

        self.update_state_switcher()

        if switch:
            log.info(f"Switching to state: {len(self.states)-1}")
            self.set_state(len(self.states)-1)

    def remove_state(self, state: int):
        d = self.identifier.get_config(self.deck_controller.active_page)

        if str(state) in d["states"]:
            d["states"].pop(str(state))

        old_loaded_state = int(self.state)

        state_to_remove = self.states.get(state)
        if state_to_remove:
            state_to_remove.close_resources()
            self.states.pop(state)

        # Fill gaps in self.states
        sorted_state_keys = sorted(self.states.keys())

        new_states = {}
        state_map = {}
        for new_key, old_key in enumerate(sorted_state_keys):
            state_map[old_key] = new_key
            self.states[old_key].state = new_key

            if self.get_active_state() is self.states[old_key]:
                self.state = new_key

            new_states[new_key] = self.states[old_key]

        self.states = new_states

        new_states_dict = {}
        for new_key, old_key in enumerate(d["states"].keys()):
            new_states_dict[str(new_key)] = d["states"][old_key]

        d["states"] = new_states_dict


        self.deck_controller.active_page.save()
        gl.page_manager.update_dict_of_pages_with_path(self.deck_controller.active_page.json_path)

        self.update_state_switcher()

        # Update - TODO: test
        if state == self.state:
            sort = sorted(list(self.states.keys()))
            sort.reverse()
            for s in sort:
                if s <= state:
                    self.set_state(s, allow_reload=True)
                    break

        gl.signal_manager.trigger_signal(Signals.RemoveState, state, state_map)

    def update_state_switcher(self):
        if gl.app.main_win.sidebar.active_identifier != self.identifier:
            return

        gl.app.main_win.sidebar.key_editor.state_switcher.set_n_states(len(self.states))

    def get_active_state(self) -> "ControllerInputState":
        return self.states.get(self.state, self.ControllerStateClass(self, -1))

    def set_state(self, state: int, update_sidebar: bool = True, allow_reload: bool = False) -> None:
        if state == self.state and not allow_reload:
            return
        
        if state not in self.states:
            log.error(f"Invalid state: {state}, must be one of {list(self.states.keys())}")
            return
        self.state = state

        self.get_active_state().update()

        if update_sidebar:
            self.reload_sidebar()

    def reload_sidebar(self) -> None:
        visible_child = gl.app.main_win.leftArea.deck_stack.get_visible_child()
        if visible_child is None:
            return
        controller = visible_child.deck_controller
        if controller is None:
            return
        
        if controller is not self.deck_controller:
            return
        if self.identifier != gl.app.main_win.sidebar.active_identifier:
            return
        
        gl.app.main_win.sidebar.active_state = self.state
        GLib.idle_add(gl.app.main_win.sidebar.update)

    def load_from_config(self, config, update: bool = True):
        n_states = len(config.get("states", {}))
        self.create_n_states(max(1, n_states))

        old_state_index = self.state

        self.state = 0

        #TODO: Reset states
        for state in config.get("states", {}):
            state: "ControllerKeyState" = self.states.get(int(state))
            if state is None:
                continue

            state_dict = config["states"][str(state.state)]

            self.get_active_state().own_actions_ready()
            # state.own_actions_ready() # Why not threaded? Because this would mean that some image changing calls might get executed after the next lines which blocks custom assets

            if update:
                self.set_state(old_state_index)
                self.update()

    def clear(self, update: bool = True):
        active_state = self.get_active_state()
        active_state.clear()
        if update:
            self.update()

    def has_unavailable_action(self) -> bool:
        for action in self.get_active_state().get_own_actions():
            if isinstance(action, ActionOutdated):
                return True
            if isinstance(action, NoActionHolderFound):
                return True
            
        return False
    
    def get_empty_background(self) -> Image.Image:
        pass

    def get_image_size(self) -> tuple[int, int]:
        pass
