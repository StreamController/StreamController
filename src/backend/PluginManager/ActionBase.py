from loguru import logger as log
from copy import copy
import subprocess
import os
import Pyro5.api

# Import own modules
from src.backend.PluginManager.Signals import Signal

# Import globals
import globals as gl

# Import locale manager
from locales.LocaleManager import LocaleManager

# Import typing
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from src.backend.PluginManager.PluginBase import PluginBase

@Pyro5.api.expose
class ActionBase:
    # Change to match your action
    ACTION_ID: str = None
    ACTION_NAME: str = None
    PLUGIN_BASE: "PluginBase" = None
    CONTROLS_KEY_IMAGE: bool = False
    KEY_IMAGE_CAN_BE_OVERWRITTEN: bool = True
    LABELS_CAN_BE_OVERWRITTEN: list[bool] = [True, True, True]

    def __init__(self, deck_controller, page, coords):
        # Verify variables
        if self.ACTION_ID in ["", None]:
            raise ValueError("Please specify an action id")


        if self.ACTION_NAME in ["", None]:
            raise ValueError("Please specify an action name")
        
        self._backend: Pyro5.api.Proxy = None
        
        self.deck_controller = deck_controller
        self.page = page
        self.page_coords = coords
        self.coords = int(coords.split("x")[0]), int(coords.split("x")[1])
        self.index = self.deck_controller.coords_to_index(self.coords)

        self.on_ready_called = False

        self.labels = {}
        self.current_key = {
            "key": self.index,
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

    def set_key(self, image = None, media_path=None, margins=[0, 0, 0, 0],
                add_background=True, loop=True, fps=30, bypass_task=False, update_ui=True, reload: bool = False):
        """
        Sets the key image for the key of the action.

        Parameters:
            image (optional): The image to be displayed.
            media_path (optional): The path to the media file.
            margins (optional): The margins for the image.
            add_background (optional): Whether to add a background.
            loop (optional): Whether to loop the video. (does only work for videos)
            fps (optional): The frames per second. (does only work for videos)
            bypass_task (optional): Whether to bypass the task.
            update_ui (optional): Whether to update the UI.
        """
        if not reload:
            self.current_key = {
                "key": self.index,
                "image": image,
                "media_path": media_path,
                "margins": margins,
                "add_background": add_background,
                "loop": loop,
                "fps": fps,
                "bypass_task": bypass_task,
                "update_ui": update_ui
            }
        elif self.current_key == {}:
            log.warning("No key to reload")
            return
        
        # Fill unset labels with labels set in the ui
        page_labels = copy(self.page.dict["keys"][self.page_coords]["labels"])
        page_labels.update(self.labels)

        self.deck_controller.set_key(**self.current_key, labels=page_labels, shrink=self.deck_controller.deck.key_states()[self.index])

    def set_label(self, text: str, position: str = "bottom", color: list[int] = [255, 255, 255], stroke_width: int = 0,
                      font_family: str = "", font_size = 18, reload: bool = True):
        if position not in ["top", "center", "bottom"]:
            raise ValueError("Position must be 'top', 'center' or 'bottom'")
        
        if text == None:
            if position in self.labels:
                del self.labels[position]
        else:
            self.labels[position] = {
                "text": text,
                "color": color,
                "stroke-width": stroke_width,
                "font-family": font_family,
                "font-size": font_size
            }

        # Reload key
        if reload:
            self.set_key(reload=True)

    def set_top_label(self, text: str, color: list[int] = [255, 255, 255], stroke_width: int = 0,
                      font_family: str = "", font_size = 18, reload: bool = True):
        self.set_label(text, "top", color, stroke_width, font_family, font_size, reload)
    
    def set_center_label(self, text: str, color: list[int] = [255, 255, 255], stroke_width: int = 0,
                      font_family: str = "", font_size = 18, reload: bool = True):
        self.set_label(text, "center", color, stroke_width, font_family, font_size, reload)
    
    def set_bottom_label(self, text: str, color: list[int] = [255, 255, 255], stroke_width: int = 0,
                      font_family: str = "", font_size = 18, reload: bool = True):
        self.set_label(text, "bottom", color, stroke_width, font_family, font_size, reload)

    def on_labels_changed_in_ui(self):
        self.set_key(reload=True)

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
        # Verify signal
        if not isinstance(signal, Signal):
            raise TypeError("signal_name must be of type Signal")
        
        # Verify callback
        if not callable(callback):
            raise TypeError("callback must be callable")
        
        # Connect
        gl.plugin_manager.connect_signal(signal = signal, callback = callback)

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