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

@Pyro5.api.expose
class PluginBase:
    plugins = {}
    
    def __init_subclass__(cls, *args, **kwargs) -> None:
        super().__init_subclass__(*args, **kwargs)
        # Change this variables in the subclasses constuctor to match your plugin
        cls.PLUGIN_NAME = ""
        cls.GITHUB_REPO = ""
        cls.ATTRIBUTIONS = {}
        cls.VERSION = "1.0"

        ## Internal variables - do not change
        cls.ACTIONS = {}
        cls.PLUGIN = None

    def __init__(self):
        self._backend: Pyro5.api.Proxy = None
        # Verify variables
        if self.PLUGIN_NAME in ["", None]:
            raise ValueError("Please specify a plugin name")
        if self.GITHUB_REPO in ["", None]:
            raise ValueError(f"Plugin: {self.PLUGIN_NAME}: Please specify a github repo")
        if self.ATTRIBUTIONS in [{}, None]:
            log.warning(f"Plugin: {self.PLUGIN_NAME}: Are you sure you don't want to add attributions?")
        if self.PLUGIN_NAME in PluginBase.plugins.keys():
            raise ValueError(f"Plugin: {self.PLUGIN_NAME}: Plugin already exists")
        # Register plugin
        PluginBase.plugins[self.PLUGIN_NAME] = {
            "object": self,
            "github": self.GITHUB_REPO,
            "attributions": self.ATTRIBUTIONS,
            "version": self.VERSION,
            "folder-path": os.path.dirname(inspect.getfile(self.__class__)),
            "file_name": os.path.basename(inspect.getfile(self.__class__))
        }
        self.PATH = os.path.dirname(inspect.getfile(self.__class__))

        self.locale_manager = LocaleManager(os.path.join(self.PATH, "locales"))

    def add_action(self, action):
        action.PLUGIN_BASE = self
        action.locale_manager = self.locale_manager
        self.ACTIONS[action.ACTION_NAME] = action

    def get_settings(self):
        if os.path.exists(os.path.join(self.PATH, "settings.json")):
            with open(os.path.join(self.PATH, "settings.json"), "r") as f:
                return json.load(f)
        return {}
    
    def set_settings(self, settings):
        with open(os.path.join(self.PATH, "settings.json"), "w") as f:
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

    @property
    def backend(self):
        # Transfer ownership
        self._backend._pyroClaimOwnership()
        return self._backend

    @backend.setter
    def backend(self, value):
        self._backend = value