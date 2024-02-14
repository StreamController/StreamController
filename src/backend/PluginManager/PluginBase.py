import os
import inspect
import json
import Pyro5.api
import subprocess

from loguru import logger as log

# Import gtk modules
import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, Gdk

# Import globals
import globals as gl

# Import own modules
from locales.LocaleManager import LocaleManager
from src.backend.PluginManager.ActionHolder import ActionHolder

@Pyro5.api.expose
class PluginBase:
    plugins = {}
    
    def __init__(self):
        self._backend: Pyro5.api.Proxy = None

        self.PATH = os.path.dirname(inspect.getfile(self.__class__))

        self.locale_manager = LocaleManager(os.path.join(self.PATH, "locales"))

        self.action_holders: dict = {}

    def register(self, plugin_name: str, github_repo: str, version: str):
        # Verify variables
        if plugin_name in ["", None]:
            raise ValueError("Please specify a plugin name")
        if github_repo in ["", None]:
            raise ValueError(f"Plugin: {plugin_name}: Please specify a github repo")
        if plugin_name in PluginBase.plugins.keys():
            raise ValueError(f"Plugin: {plugin_name}: Plugin already exists")
        
        # Register plugin
        PluginBase.plugins[plugin_name] = {
            "object": self,
            "github": github_repo,
            "version": version,
            "folder-path": os.path.dirname(inspect.getfile(self.__class__)),
            "file_name": os.path.basename(inspect.getfile(self.__class__))
        }

        self.plugin_name = plugin_name
        self.github_repo = github_repo
        self.version = version


    def add_action(self, action_class: type, action_id: str, action_name: str):
        raise NotImplementedError
        action_class.PLUGIN_BASE = self
        self.ACTIONS[action_id] = {
            "class": action_class,
            "name": action_name
        }


        return
        if not self.verify_action(action):
            return
        action.PLUGIN_BASE = self
        action.locale_manager = self.locale_manager
        self.ACTIONS[action.ACTION_ID] = action
        print(f"actions: {self.ACTIONS}")

    def add_action_holder(self, action_holder: ActionHolder):
        if not isinstance(action_holder, ActionHolder):
            raise ValueError("Please pass an ActionHolder")
        
        self.action_holders[action_holder.action_id] = action_holder

    def verify_action(self, action) -> bool:
        if action.ACTION_ID in self.ACTIONS:
            log.error(f"Plugin: {self.PLUGIN_NAME}: Action ID already exists, skipping")
            return False
        
        elif action.get_name() in [None, ""]:
            log.error(f"Plugin: {self.PLUGIN_NAME}: Please specify an action name for action with id {action.ACTION_ID}, skipping")
            return False
        
        elif action.ACTION_ID in [None, ""]:
            log.error(f"Plugin: {self.PLUGIN_NAME}: Please specify an action id for action with name {action.get_name()}, skipping")
            return False
        
        return True

    def get_settings(self):
        if os.path.exists(os.path.join(gl.DATA_PATH, "settings.json")):
            with open(os.path.join(gl.DATA_PATH, "settings.json"), "r") as f:
                return json.load(f)
        return {}
    
    def set_settings(self, settings):
        with open(os.path.join(gl.DATA_PATH, "settings.json"), "w") as f:
            json.dump(settings, f, indent=4)

    def add_css_stylesheet(self, path):
        css_provider = Gtk.CssProvider()
        css_provider.load_from_path(path)
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(),
            css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

    def register_page(self, path: str) -> None:
        gl.page_manager.register_page(path)

    def launch_backend(self, backend_path: str, venv_path: str = None):
        uri = self.add_to_pyro()

        ## Launch
        command = ""
        if venv_path is not None:
            command = f"source {venv_path}/bin/activate && "
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
        # Transfer ownership
        if self._backend is not None:
            self._backend._pyroClaimOwnership()
        return self._backend

    @backend.setter
    def backend(self, value):
        self._backend = value