import os
import importlib
import sys
from loguru import logger as log

from src.backend.PluginManager.PluginBase import PluginBase
from src.backend.DeckManagement.HelperMethods import get_last_dir

class PluginManager:
    action_index = {}
    def __init__(self):
        self.initialized_plugin_classes = list[PluginBase]()

    def load_plugins(self):
        # get all folders in plugins folder
        if not os.path.exists("plugins"):
            os.mkdir("plugins")
        folders = os.listdir("plugins")
        for folder in folders:
            # Import main module
            import_string = f"plugins.{folder}.main"
            if import_string not in sys.modules.keys():
                # Import module only if it's not already imported
                importlib.import_module(f"plugins.{folder}.main")

        # Get all classes inheriting from PluginBase and generate objects for them
        self.init_plugins()

    def init_plugins(self):
        subclasses = PluginBase.__subclasses__()
        for subclass in subclasses:
            if subclass in self.initialized_plugin_classes:
                print("skippting, already initialized")
                continue
            obj = subclass()
            self.initialized_plugin_classes.append(subclass)

    def generate_action_index(self):
        plugins = self.get_plugins()
        for plugin in plugins.keys():
            if plugin in self.action_index.keys():
                continue
            for action in plugins[plugin]["object"].ACTIONS.keys():
                path = plugins[plugin]["folder-path"]
                # Remove everything except the last folder
                path = get_last_dir(path)
                self.action_index[f"{path}::{action}"] = plugins[plugin]["object"].ACTIONS[action]
            
    def get_plugins(self):
        return PluginBase.plugins
    
    def get_actions_for_plugin(self, plugin_name):
        return PluginBase.plugins[plugin_name]["object"].ACTIONS
    
    def get_action_from_action_string(self, action_string: str):
        """
        Example string: dev_core447_MediaPlugin::Pause
        """
        try:
            return self.action_index[action_string]
        except KeyError:
            log.warning(f"Requested action {action_string} not found, skipping...")
            return None
        
    def get_action_string_from_action(self, action):
        for key, value in self.action_index.items():
            if value == action:
                return key
            
    def get_plugin_by_id(self, plugin_id:str) -> PluginBase:
        plugins = self.get_plugins()
        for plugin in plugins.keys():
            _id = get_last_dir(plugins[plugin]["folder-path"])
            if _id == plugin_id:
                return plugins[plugin]["object"]