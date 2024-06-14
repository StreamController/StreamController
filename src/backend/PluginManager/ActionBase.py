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
from src.backend.DeckManagement.InputIdentifier import Input, InputEvent, InputIdentifier

# Import globals
import globals as gl

# Import locale manager
from locales.LegacyLocaleManager import LegacyLocaleManager

# Import typing
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from src.backend.PluginManager.PluginBase import PluginBase
    from src.backend.DeckManagement.DeckController import DeckController, ControllerKey, ControllerKeyState
    from src.backend.PageManagement.Page import Page

class ActionBase(rpyc.Service):
    # Change to match your action
    def __init__(self, action_id: str, action_name: str,
                 deck_controller: "DeckController", page: "Page", plugin_base: "PluginBase", state: int,
                 input_ident: "InputIdentifier"):
        #TODO: Add state arg to all init methods
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

        self.CONTROLS_KEY_IMAGE: bool = False
        self.KEY_IMAGE_CAN_BE_OVERWRITTEN: bool = True
        self.LABELS_CAN_BE_OVERWRITTEN: list[bool] = [True, True, True]
        self.has_configuration = False

        self.labels = {}
#        self.current_key = {
#            "key": self.key_index,
#            "image": None,
#        }
        
        self.default_image = None
        self.default_labels = {}

        self.locale_manager: LegacyLocaleManager = None

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
        ## backward compatibility
        if event == Input.Key.Events.DOWN:
            self.on_key_down()
        elif event == Input.Key.Events.UP:
            self.on_key_up()
        elif event == Input.Dial.Events.DOWN:
            self.on_key_down()
        elif event == Input.Dial.Events.UP:
            self.on_key_up()

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
        self.on_ready() # backward compatibility

    def on_touch_swipe_left(self):
        # Fallback to normal on_key_down
        self.on_key_down()

    def on_touch_swipe_right(self):
        # Fallback to normal on_key_down
        self.on_key_down()

    def on_touch_down(self):
        # Fallback to normal on_key_down
        self.on_key_down()

    def on_touch_up(self):
        # Fallback to normal on_key_up
        self.on_key_up()

    def on_dial_cw(self):
        # Fallback to normal on_key_down
        self.on_key_down()

    def on_dial_ccw(self):
        # Fallback to normal on_key_down
        self.on_key_down()

    def on_dial_down(self):
        # Fallback to normal on_key_down
        self.on_key_down()

    def on_dial_up(self):
        # Fallback to normal on_key_up
        self.on_key_up()

    def set_default_image(self, image: Image.Image):
        self.default_image = image

    def set_default_label(self, text: str, position: str = "bottom", color: list[int] = [255, 255, 255], stroke_width: int = 0, 
                          font_family: str = "", font_size = 18):
        log.warning("set_default_label is not yet supported, please use fixed or no lables for now")
        """
        Not yet implemented, changes made through this function will be ignored
        """
        if position not in ["top", "center", "bottom"]:
            raise ValueError("Position must be 'top', 'center' or 'bottom'")
        
        if text == None:
            if position in self.default_labels:
                del self.default_labels[position]
        else:
            self.default_labels[position] = {
                "text": text,
                "color": color,
                "stroke-width": stroke_width,
                "font-family": font_family,
                "font-size": font_size
            }

    def set_media(self, image = None, media_path=None, size: float = None, valign: float = None, halign: float = None, fps: int = 30, loop: bool = True, update: bool = True):
        if type(self.input_ident) not in [Input.Key, Input.Dial]:
            return

        if not self.get_is_present(): return
        if self.has_custom_user_asset(): return
        # if not self.has_image_control(): return #TODO
        
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

        if image is not None or media_path is None:
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

        self.get_state().layout_manager.set_action_layout(ImageLayout(
            valign=valign,
            halign=halign,
            size=size
        ), update=False)

        if update:
            self.get_input().update()

    def set_background_color(self, color: list[int] = [255, 255, 255, 255], update: bool = True):
        if not self.on_ready_called:
            update = False
        if self.key_index >= self.deck_controller.deck.key_count():
            return
        if self.get_state() is None or self.get_state().state != self.state: return

        self.get_state().background_color = color
        if update:
            self.get_input().update()

    def show_error(self, duration: int = -1) -> None:
        if not self.get_is_present(): return
        if self.get_is_multi_action(): return
        try:
            self.get_input_state().show_error(duration=duration)
        except AttributeError:
            pass

    def hide_error(self) -> None:
        if not self.get_is_present(): return
        if self.get_is_multi_action(): return
        try:
            self.get_input_state().hide_error()
        except AttributeError:
            pass

    def set_label(self, text: str, position: str = "bottom", color: list[int] = None,
                      font_family: str = None, font_size = None, update: bool = True):
        if type(self.input_ident) not in [Input.Key, Input.Dial]:
            return
        
        if not self.get_is_present():
            return
        if not self.on_ready_called:
            update = False
            update = True #FIXME
        if self.get_state() is None or self.get_state().state != self.state: return

        label_index = 0 if position == "top" else 1 if position == "center" else 2

        if not self.has_label_control()[label_index]:
            return
        
        if text is None:
            text = ""

        self.labels[position] = {
            "text": text,
            "color": color,
            "font-family": font_family,
            "font-size": font_size
        }
        
        key_label = KeyLabel(
            controller_input=self.get_state().controller_input,
            text=text,
            font_size=font_size,
            font_name=font_family,
            color=color,
        )
        self.get_state().label_manager.set_action_label(label=key_label, position=position, update=update)

    def set_top_label(self, text: str, color: list[int] = None,
                      font_family: str = None, font_size = None, update: bool = True):
        self.set_label(text, "top", color, font_family, font_size, update)

    def set_center_label(self, text: str, color: list[int] = None,
                      font_family: str = None, font_size = None, update: bool = True):
        self.set_label(text, "center", color, font_family, font_size, update)

    def set_bottom_label(self, text: str, color: list[int] = None,
                      font_family: str = None, font_size = None, update: bool = True):
        self.set_label(text, "bottom", color, font_family, font_size, update)

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
    
    def get_is_multi_action(self) -> bool:
        if not self.get_is_present(): return
        actions = self.page.action_objects.get(self.input_ident.input_type, {}).get(self.input_ident.json_identifier, [])
        return len(actions) > 1
    
    def has_label_control(self) -> list[bool]:
        key_dict = self.input_ident.get_config(self.page).get("states", {}).get(str(self.state), {})

        return [i == self.get_own_action_index() for i in key_dict.get("label-control-actions", [None, None, None])]

    def has_image_control(self):
        key_dict = self.input_ident.get_config(self.page).get("states", {}).get(str(self.state), {})

        if key_dict.get("image-control-action") is None:
            return False
        
        if not self.get_is_multi_action():
            return True

        return self.get_own_action_index() == key_dict.get("image-control-action")
    
    def get_is_present(self):
        if self.page is None: return False
        if self.page.deck_controller.active_page is not self.page: return False
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
    
    def set_dial_touch_image(self, image: Image.Image = None, image_path: str = None) -> None:
        if not isinstance(self.input_ident, Input.Dial):
            return

        if image_path is not None:
            image = Image.open(image_path)
        touch_screen = self.deck_controller.get_input(Input.Touchscreen("sd-plus"))
        state = touch_screen.get_active_state()
        state.set_dial_image(self.input_ident, image)

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
                assignments[event] = Input.EventFromStringName(page_assignment_dict[event.string_name])
            else:
                assignments[event] = event

        return assignments
    
    def set_event_assignments(self, assignments: dict[InputEvent, InputEvent]):
        assignments_strings = {}

        for key, value in assignments.items():
            if key == value:
                continue

            assignments_strings[key.string_name] = value.string_name

        self.page.set_action_event_assignments(action_object=self, event_assignments=assignments_strings)

    
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

        ## Launch
        if open_in_terminal:
            command = "gnome-terminal -- bash -c '"
            if venv_path is not None:
                command += "source {venv_path}/bin/activate && "
            command += f"python3 {backend_path} --port={port}; exec $SHELL'"
        else:
            command = ""
            if venv_path is not None:
                command = f"source {venv_path}/bin/activate && "
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
        pass