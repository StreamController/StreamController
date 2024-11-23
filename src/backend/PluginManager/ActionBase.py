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
import threading
import time
from loguru import logger as log
from copy import copy
import subprocess
import os
from PIL import Image

import rpyc
from rpyc.utils.server import ThreadedServer
from rpyc.core.protocol import Connection
from rpyc.core import netref

# Import own modules
from src.Signals.Signals import Signal
from src.backend.DeckManagement.HelperMethods import is_image, is_svg, is_video
from src.backend.DeckManagement.Subclasses.KeyImage import InputImage
from src.backend.DeckManagement.Subclasses.KeyVideo import InputVideo
from src.backend.DeckManagement.Subclasses.KeyLabel import KeyLabel
from src.backend.DeckManagement.Subclasses.KeyLayout import ImageLayout
from src.backend.DeckManagement.Media.Media import Media
from src.backend.DeckManagement.InputIdentifier import Input, InputEvent, InputIdentifier

# Import globals
import globals as gl

# Import typing
from typing import TYPE_CHECKING

from src.backend.PluginManager.PluginSettings.Asset import Color,Icon

if TYPE_CHECKING:
    from src.backend.PluginManager.PluginBase import PluginBase
    from src.backend.DeckManagement.DeckController import DeckController, ControllerKey, ControllerKeyState
    from src.backend.PageManagement.Page import Page
    from src.backend.DeckManagement.DeckController import ControllerInput, ControllerInputState

class ActionBase(rpyc.Service):
    # Change to match your action
    def __init__(self, action_id: str, action_name: str,
                 deck_controller: "DeckController", page: "Page", plugin_base: "PluginBase", state: int,
                 input_ident: "InputIdentifier"):
        self.backend_connection: Connection = None
        self.backend: netref = None
        self.server: ThreadedServer = None
        
        self.deck_controller = deck_controller
        self.page = page
        self.state = state
        self.input_ident = input_ident
        self.action_id = action_id
        self.action_name = action_name
        self.plugin_base = plugin_base

        self.on_ready_called = False

        self.has_configuration = False
        self.allow_event_configuration: bool = True

        self.labels = {}

        log.info(f"Loaded action {self.action_name} with id {self.action_id}")
        
    def set_deck_controller(self, deck_controller):
        """
        Internal function, do not call manually
        """
        self.deck_controller = deck_controller
 
    def set_page(self, page):
        """
        Internal function, do not call manually
        """
        self.page = page

    def get_input(self) -> "ControllerInput":
        return self.deck_controller.get_input(self.input_ident)
    
    def get_state(self) -> "ControllerInputState":
        i = self.get_input()
        if i is None: return
        return i.states.get(self.state)
    
    def event_callback(self, event: InputEvent, data: dict = None):
        # TODO: Rename to on_event
        ## backward compatibility
        if event == Input.Key.Events.DOWN:
            self.on_key_down()
        elif event == Input.Key.Events.UP:
            self.on_key_up()
        elif event == Input.Dial.Events.DOWN:
            self.on_key_down()
        elif event == Input.Dial.Events.UP:
            self.on_key_up()
        elif event == Input.Dial.Events.SHORT_TOUCH_PRESS:
            self.on_key_down()

    def on_key_down(self):
        pass

    def on_key_up(self):
        pass

    def on_tick(self):
        pass

    def on_ready(self):
        """
        This method is called when the page is ready to process requests made by the actions.
        Setting the default image in this method is recommended over setting it in the constructor.
        """
        pass

    def on_update(self):
        """
        This method gets called when the app wants the action to redraw itself (image, labels, etc.).
        """
        self.on_ready() # backward compatibility

    def set_media(self, image = None, media_path=None, size: float = None, valign: float = None, halign: float = None, fps: int = 30, loop: bool = True, update: bool = True):
        self.raise_error_if_not_ready()

        if type(self.input_ident) not in [Input.Key, Input.Dial]:
            return

        if not self.get_is_present(): return
        if self.has_custom_user_asset(): return
        if not self.has_image_control(): return #TODO
        
        input_state = self.get_state()

        if input_state is None:
            return
        if self.get_state().state != self.state:
            return

        if is_image(media_path) and image is None:
            with Image.open(media_path) as img:
                image = img.copy()

        if is_svg(media_path) and image is None:
            image = gl.media_manager.generate_svg_thumbnail(media_path)

        if image is not None:
            input_state.set_image(InputImage(
                controller_input=self.get_state().controller_input,
                image=image,
            ), update=False)

        elif is_video(media_path):
            input_state.set_video(InputVideo(
                controller_input=self.get_state().controller_input,
                video_path=media_path,
                fps=fps,
                loop=loop
            ))

        else:
            input_state.set_image(None, update=False)

        self.get_state().layout_manager.set_action_layout(ImageLayout(
            valign=valign,
            halign=halign,
            size=size
        ), update=False)

        if update:
            self.get_input().update()

    def set_background_color(self, color: list[int] = [255, 255, 255, 255], update: bool = True):
        self.raise_error_if_not_ready()

        if not self.get_is_present(): return

        if not self.has_background_control(): return

        if not self.on_ready_called:
            update = False

        state = self.get_state()
        if state is None or state.state != self.state: return

        state.background_manager.set_action_color(color)
        if update:
            self.get_input().update()

    def show_error(self, duration: int = -1) -> None:
        self.raise_error_if_not_ready()

        if not self.get_is_present(): return
        if self.get_is_multi_action(): return
        try:
            self.get_state().show_error(duration=duration)
        except AttributeError as e:
            log.error(e)
            pass

    def hide_error(self) -> None:
        self.raise_error_if_not_ready()

        if not self.get_is_present(): return
        if self.get_is_multi_action(): return
        try:
            self.get_state().hide_error()
        except AttributeError:
            pass

    def set_label(self, text: str, position: str = "bottom", color: list[int]=None,
                  font_family: str=None, font_size=None, outline_width: int = None, outline_color: list[int] = None,
                  font_weight: int = None, font_style: str = None,
                  update: bool=True):
        self.raise_error_if_not_ready()

        if type(self.input_ident) not in [Input.Key, Input.Dial]:
            return
        
        if self.get_state() is None:
            log.error(f"Could not find state, action: {self.action_id}, state: {self.state}")
            return
        
        if not self.get_is_present():
            return
        if not self.on_ready_called:
            update = False
            update = True #FIXME

        if font_style not in ["normal", "italic", "oblique", None]:
            raise ValueError("font_style must be one of ['normal', 'italic', 'oblique', None]")

        label_index = 0 if position == "top" else 1 if position == "center" else 2

        if not self.has_label_control(label_index):
            return
        
        if text is None:
            text = ""

        text = str(text)

        self.labels[position] = {
            "text": text,
            "color": color,
            "font-family": font_family,
            "font-size": font_size,
            "outline_width": outline_width,
            "outline_color": outline_color,
            "font-weight": font_weight,
            "font-style": font_style
        }
        
        key_label = KeyLabel(
            controller_input=self.get_state().controller_input,
            text=text,
            font_size=font_size,
            font_name=font_family,
            color=color,
            outline_width=outline_width,
            outline_color=outline_color,
            font_weight=font_weight,
            style=font_style
        )
        self.get_state().label_manager.set_action_label(label=key_label, position=position, update=update)

    def set_top_label(self, text: str, color: list[int] = None,
                      font_family: str = None, font_size = None, outline_width: int = None, outline_color: list[int] = None,
                      font_weight: int = None, font_style: str = None,
                      update: bool = True):
        self.set_label(text, "top", color, font_family, font_size, outline_width, outline_color, font_weight, font_style, update)

    def set_center_label(self, text: str, color: list[int] = None,
                      font_family: str = None, font_size = None, outline_width: int = None, outline_color: list[int] = None,
                      font_weight: int = None, font_style: str = None,
                      update: bool = True):
        self.set_label(text, "center", color, font_family, font_size, outline_width, outline_color, font_weight, font_style, update)

    def set_bottom_label(self, text: str, color: list[int] = None,
                      font_family: str = None, font_size = None, outline_width: int = None, outline_color: list[int] = None,
                      font_weight: int = None, font_style: str = None,
                      update: bool = True):
        self.set_label(text, "bottom", color, font_family, font_size, outline_width, outline_color, font_weight, font_style, update)

    def on_labels_changed_in_ui(self):
        # TODO
        pass

    def get_config_rows(self) -> "list[Adw.PreferencesRow]":
        return []
    
    def get_custom_config_area(self):
        return
    
    def get_settings(self) -> dir:
        # self.page.load()
        if self.page is None:
            return {}
        return self.page.get_action_settings(action_object=self)
    
    def set_settings(self, settings: dict):
        if self.page is None:
            return
        self.page.set_action_settings(action_object=self, settings=settings)

    def connect(self, signal:Signal = None, callback: callable = None) -> None:
        # Connect
        gl.signal_manager.connect_signal(signal = signal, callback = callback)

    def get_own_key(self) -> "ControllerKey":
        return self.deck_controller.keys[self.key_index]
    
    def get_is_multi_action(self) -> bool:
        self.raise_error_if_not_ready()

        if not self.get_is_present(): return
        actions = self.page.action_objects.get(self.input_ident.input_type, {}).get(self.input_ident.json_identifier, [])
        return len(actions) > 1

    def get_asset_path(self, asset_name: str, subdirs: list[str] = None, asset_folder: str = "assets") -> str:
        """
        Helper method that returns paths to plugin assets.

        Args:
            asset_name (str): Name of the Asset File
            subdirs (list[str], optional): Subdirectories. Defaults to [].
            asset_folder (str, optional): Name of the folder where assets are stored. Defaults to "assets".

        Returns:
            str: The full path to the asset
        """

        if not subdirs:
            return os.path.join(self.plugin_base.PATH, asset_folder, asset_name)

        subdir = os.path.join(*subdirs)
        if subdir != "":
            return os.path.join(self.plugin_base.PATH, asset_folder, subdir, asset_name)
        return ""

    def get_icon(self, key: str, skip_override: bool = False) -> Icon | None:
        return self.plugin_base.asset_manager.icons.get_asset(key, skip_override)

    def get_color(self, key: str, skip_override: bool = False) -> Color | None:
        return self.plugin_base.asset_manager.colors.get_asset(key, skip_override)

    def get_translation(self, key: str, fallback: str = None):
        self.plugin_base.locale_manager.get(key, fallback)
    
    def has_label_controls(self):
        own_action_index = self.get_own_action_index()
        return [own_action_index == i for i in self.get_state().action_permission_manager.get_label_control_indices()]
    
    def has_label_control(self, label_index) -> list[bool]:
        #TODO: Might require performance improvements
        return self.get_state().action_permission_manager.get_label_control_index(label_index) == self.get_own_action_index()

    def has_image_control(self):
        #TODO: Might require performance improvements
        image_control_index = self.get_state().action_permission_manager.get_image_control_index()
        return image_control_index == self.get_own_action_index()


        key_dict = self.input_ident.get_config(self.page).get("states", {}).get(str(self.state), {})

        if key_dict.get("image-control-action") is None:
            return False
        
        if ("image-control-action" not in key_dict) and (not self.get_is_multi_action()):
            return True

        return self.get_own_action_index() == key_dict.get("image-control-action")
    
    def has_background_control(self):
        #TODO: Might require performance improvements
        background_control_index = self.get_state().action_permission_manager.get_background_control_index()
        return background_control_index == self.get_own_action_index()
    
    def get_is_present(self):
        if self.page is None: return False
        if self.page.deck_controller.active_page is not self.page: return False
        if self.page.deck_controller.screen_saver.showing: return False
        # if self.state != self.get_state().state: return False #TODO: Check for touchscreen and dial states
        return self in self.page.get_all_actions()
    
    def has_custom_user_asset(self) -> bool:
        if not self.get_is_present(): return False
        media = self.input_ident.get_config(self.page).get("states", {}).get(str(self.state), {}).get("media", {})
        return media.get("path", None) is not None
    
    def get_own_action_index(self) -> int:
        if not self.get_is_present(): return -1
        actions = self.page.get_all_actions_for_input(self.input_ident, self.state)
        if self not in actions:
            return
        return actions.index(self)

    def get_page_event_assignments(self) -> dict[InputEvent, InputEvent]:
        assignment = {}

        page_assignment_dict = self.page.get_action_event_assignments(action_object=self)

        all_events = Input.AllEvents()
        for event in all_events:
            if event.string_name in page_assignment_dict:
                assignment[event] = Input.EventFromStringName(page_assignment_dict[event.string_name])
            else:
                assignment[event] = event

        return assignment
    
    def get_event_assignments(self) -> dict[InputEvent, InputEvent]:
        assignments = {}

        page_assignment_dict = self.page.get_action_event_assignments(action_object=self)

        all_events = Input.AllEvents()
        for event in all_events:
            if event.string_name in page_assignment_dict:
                assignments[event] = Input.EventFromStringName(page_assignment_dict[str(event)])
            else:
                assignments[event] = event

        return assignments
    
    def set_event_assignments(self, assignments: dict[InputEvent, InputEvent]):
        assignments_strings = {}

        for key, value in assignments.items():
            if key == value:
                continue

            assignments_strings[str(key)] = str(value)

        self.page.set_action_event_assignments(action_object=self, event_assignments=assignments_strings)

    
    def raise_error_if_not_ready(self):
        if self.on_ready_called:
            return
        raise Warning("Seems like you're calling this method before the action is ready")
    
    # ---------- #
    # Rpyc stuff #
    # ---------- #

    def start_server(self):
        if self.server is not None:
            log.warning("Server already running, skipping...")
            return
        self.server = ThreadedServer(self, hostname="localhost", port=0, protocol_config={"allow_public_attrs": True})
        threading.Thread(target=self.server.start, name="server_start", daemon=True).start()

    def on_disconnect(self):
        if self.server is not None:
            self.server.close()
        if self.backend_connection is not None:
            self.backend_connection.close()
        self.backend = None
    
    def launch_backend(self, backend_path: str, venv_path: str = None, open_in_terminal: bool = False):
        self.start_server()
        port = self.server.port

        if venv_path is not None:
            if not os.path.exists(venv_path):
                raise ValueError(f"Venv path does not exist: {venv_path}")
        if backend_path is None:
            if  not os.path.exists(backend_path):
                raise ValueError(f"Backend path does not exist: {backend_path}")

        ## Launch
        if open_in_terminal:
            command = "gnome-terminal -- bash -c '"
            if venv_path is not None:
                command += f". {venv_path}/bin/activate && "
            command += f"python3 {backend_path} --port={port}; exec $SHELL'"
        else:
            command = ""
            if venv_path is not None:
                command = f". {venv_path}/bin/activate && "
            command += f"python3 {backend_path} --port={port}"

        log.info(f"Launching backend: {command}")
        subprocess.Popen(command, shell=True, start_new_session=open_in_terminal)

        self.wait_for_backend()

    def wait_for_backend(self, tries: int = 3):
        while tries > 0 and self.backend_connection is None:
            time.sleep(0.1)
            tries -= 1

    def register_backend(self, port: int):
        """
        Internal method, do not call manually
        """
        self.backend_connection = rpyc.connect("localhost", port)
        self.backend = self.backend_connection.root
        gl.plugin_manager.backends.append(self.backend_connection)
        self.on_backend_ready()

    def on_backend_ready(self):
        pass

    def ping(self) -> bool:
        return True
    
    def on_removed_from_cache(self) -> None:
        #TODO: Fully implement
        pass

    def on_remove(self) -> None:
        #TODO: Fully implement
        pass
