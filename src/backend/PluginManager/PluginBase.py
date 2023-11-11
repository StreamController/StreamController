import os
import inspect
import json

from loguru import logger as log

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

    def add_action(self, action):
        action.PLUGIN_BASE = self
        self.ACTIONS[action.ACTION_NAME] = action

    def get_settings(self):
        if os.path.exists(os.path.join(self.PATH, "settings.json")):
            with open(os.path.join(self.PATH, "settings.json"), "r") as f:
                return json.load(f)
        return {}
    
    def set_settings(self, settings):
        with open(os.path.join(self.PATH, "settings.json"), "w") as f:
            json.dump(settings, f, indent=4)
