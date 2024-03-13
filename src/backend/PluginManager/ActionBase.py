from loguru import logger as log
from copy import copy
import subprocess
import os
import Pyro5.api
from PIL import Image

# Import own modules
from src.Signals.Signals import Signal
from src.backend.PageManagement.Page import Page
from src.backend.DeckManagement.HelperMethods import is_image, is_video
from src.backend.DeckManagement.DeckController import KeyImage, KeyVideo, BackgroundImage, BackgroundVideo, KeyLabel

# Import globals
import globals as gl

# Import locale manager
from locales.LocaleManager import LocaleManager

# Import typing
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from src.backend.PluginManager.PluginBase import PluginBase
    from src.backend.DeckManagement.DeckController import DeckController, ControllerKey

@Pyro5.api.expose
class ActionBase:
    # Change to match your action
    ACTION_ID: str = None
    ACTION_NAME: str = None
    CONTROLS_KEY_IMAGE: bool = False
    KEY_IMAGE_CAN_BE_OVERWRITTEN: bool = True
    LABELS_CAN_BE_OVERWRITTEN: list[bool] = [True, True, True]

    def __init__(self, action_id: str, action_name: str,
                 deck_controller: "DeckController", page: Page, coords: str, plugin_base: "PluginBase"):
        self._backend: Pyro5.api.Proxy = None
        
        self.deck_controller = deck_controller
        self.page = page
        self.page_coords = coords
        self.coords = int(coords.split("x")[0]), int(coords.split("x")[1])
        self.key_index = self.deck_controller.coords_to_index(self.coords)
        self.action_id = action_id
        self.action_name = action_name
        self.plugin_base = plugin_base

        self.on_ready_called = False

        self.labels = {}
        self.current_key = {
            "key": self.key_index,
            "image": None,
         }
        
        self.default_image = None
        self.default_labels = {}

        self.locale_manager: LocaleManager = None

        log.info(f"Loaded action {self.ACTION_NAME}")
        
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

    def set_coords(self, coords):
        """
        Internal function, do not call manually
        """
        self.coords = coords
    
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

    def on_tick(self):
        pass

    def set_default_image(self, image: "PIL.Image"):
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

    def set_media(self, image = None, media_path=None, size: float = 1, valign: float = 0, halign: float = 0, update: bool = True):
        # Block for multi actions
        if self.get_is_multi_action():
            return
        
        if is_image(media_path):
            with Image.open(media_path) as img:
                image = img.copy()

        if image is not None:
            self.deck_controller.keys[self.key_index].set_key_image(KeyImage(
                controller_key=self.deck_controller.keys[self.key_index],
                image=image,
                size=size,
                valign=valign,
                halign=halign
            ), update=False)
        if is_video(media_path):
            self.deck_controller.keys[self.key_index].set_key_video(KeyVideo(
                controller_key=self.deck_controller.keys[self.key_index],
                video_path=media_path,
            ))

        if update:
            self.deck_controller.update_key(self.key_index)
            
    def show_error(self, duration: int = -1) -> None:
        self.deck_controller.keys[self.key_index].show_error(duration=duration)
        

    def set_label(self, text: str, position: str = "bottom", color: list[int] = [255, 255, 255], stroke_width: int = 0,
                      font_family: str = "", font_size = 18, update: bool = True):
        
        self.labels[position] = {
            "text": text,
            "color": color,
            "stroke-width": stroke_width,
            "font-family": font_family,
            "font-size": font_size
        }
        
        key_label = KeyLabel(
            controller_key=self.deck_controller.keys[self.key_index],
            text=text,
            font_size=font_size,
            font_name=font_family,
            color=color,
            font_weight=stroke_width
        )
        self.deck_controller.keys[self.key_index].add_label(key_label, position=position, update=update)

    def set_top_label(self, text: str, color: list[int] = [255, 255, 255], stroke_width: int = 0,
                      font_family: str = "", font_size = 18, update: bool = True):
        self.set_label(text, "top", color, stroke_width, font_family, font_size, update)
    
    def set_center_label(self, text: str, color: list[int] = [255, 255, 255], stroke_width: int = 0,
                      font_family: str = "", font_size = 18, update: bool = True):
        self.set_label(text, "center", color, stroke_width, font_family, font_size, update)
    
    def set_bottom_label(self, text: str, color: list[int] = [255, 255, 255], stroke_width: int = 0,
                      font_family: str = "", font_size = 18, update: bool = True):
        self.set_label(text, "bottom", color, stroke_width, font_family, font_size, update)

    def on_labels_changed_in_ui(self):
        # TODO
        pass

    def get_config_rows(self) -> "list[Adw.PreferencesRow]":
        return []
    
    def get_custom_config_area(self):
        return
    
    def get_settings(self) -> dir:
        # self.page.load()
        return self.page.get_settings_for_action(self, coords = self.page_coords)
    
    def set_settings(self, settings: dict):
        self.page.set_settings_for_action(self, settings=settings, coords = self.page_coords)
        self.page.save()

    def connect(self, signal:Signal = None, callback: callable = None) -> None:
        # Connect
        gl.signal_manager.connect_signal(signal = signal, callback = callback)

    def launch_backend(self, backend_path: str, venv_activate_path: str = None):
        uri = self.add_to_pyro()

        ## Launch
        command = ""
        if venv_activate_path is not None:
            command = f"source{venv_activate_path} && "
        command += "python3 "
        command += f"{backend_path}"
        command += f" --uri={uri}"

        subprocess.Popen(command, shell=True, start_new_session=True)

    def add_to_pyro(self) -> str:
        daemon = gl.plugin_manager.pyro_daemon
        uri = daemon.register(self)
        return str(uri)
    
    def register_backend(self, backend_uri:str):
        """
        Internal method, do not call manually
        """
        self._backend = Pyro5.api.Proxy(backend_uri)
        gl.plugin_manager.backends.append(self._backend)

    @property
    def backend(self):
        if self._backend is not None:
            # Transfer ownership
            self._backend._pyroClaimOwnership()
        return self._backend

    @backend.setter
    def backend(self, value):
        self._backend = value

    def get_own_key(self) -> "ControllerKey":
        return self.deck_controller.keys[self.key_index]
    
    def get_is_multi_action(self) -> bool:
        actions = self.page.action_objects[self.page_coords]
        return len(actions) > 1