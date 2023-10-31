import os
import inspect

from loguru import logger as log

class PluginBase:
    # Change this variables to match your plugin
    PLUGIN_NAME = "" # This name will be shown in the ui
    GITHUB_REPO = "" # Link to the github repo
    ATTRIBUTIONS = {} # See documentation
    VERSION = "1.0"

    ## Internal variables - do not change
    ACTIONS = {}
    plugins = {}
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

    def add_action(self, action):
        self.ACTIONS[action.ACTION_NAME] = action