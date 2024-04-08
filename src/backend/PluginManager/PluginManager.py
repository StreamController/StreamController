import os
import importlib
import sys
from loguru import logger as log
import threading

# Import own modules
from src.backend.PluginManager.ActionHolder import ActionHolder
from src.backend.PluginManager.PluginBase import PluginBase
from src.backend.DeckManagement.HelperMethods import get_last_dir
from streamcontroller_plugin_tools import BackendBase

import globals as gl

class PluginManager:
    action_index = {}
    def __init__(self):
        self.initialized_plugin_classes = list[PluginBase]()
        self.backends:list[BackendBase] = []

    def load_plugins(self):
        # get all folders in plugins folder
        if not os.path.exists(os.path.join(gl.DATA_PATH, "plugins")):
            os.mkdir(os.path.join(gl.DATA_PATH, "plugins"))
        folders = os.listdir(os.path.join(gl.DATA_PATH, "plugins"))
        for folder in folders:
            # Import main module
            import_string = f"plugins.{folder}.main"
            if import_string not in sys.modules.keys():
                # Import module only if it's not already imported
                try:
                    importlib.import_module(f"plugins.{folder}.main")
                except Exception as e:
                    log.error(f"Error importing plugin {folder}: {e}")

        # Get all classes inheriting from PluginBase and generate objects for them
        self.init_plugins()

    def init_plugins(self):
        subclasses = PluginBase.__subclasses__()
        for subclass in subclasses:
            if subclass in self.initialized_plugin_classes:
                log.info(f"Skipping {subclass} because it's already initialized")
                continue
            try:
                obj = subclass()
            except Exception as e:
                log.error(f"Error initializing plugin {subclass}: {e}. Skipping...")
                continue
            self.initialized_plugin_classes.append(subclass)

    def generate_action_index(self):
        plugins = self.get_plugins()
        for plugin in plugins.values():
            plugin_base = plugin["object"]
            holders = plugin_base.action_holders
            self.action_index.update(plugin_base.action_holders)

        return
        plugins = self.get_plugins()
        for plugin in plugins.keys():
            if plugin in self.action_index.keys():
                continue
            for action_id in plugins[plugin]["object"].ACTIONS.keys():
                if action_id is None:
                    log.warning(f"Plugin {plugin} has an action with id None, skipping...")
                    continue

                path = plugins[plugin]["folder-path"]
                # Remove everything except the last folder
                path = get_last_dir(path)
                self.action_index[action_id] = plugins[plugin]["object"].ACTIONS[action_id]

    def get_plugins(self) -> list[PluginBase]:
        return PluginBase.plugins
    
    def get_actions_for_plugin(self, plugin_name):
        return PluginBase.plugins[plugin_name]["object"].ACTIONS
    
    def get_action_holder_from_id(self, action_id: str) -> ActionHolder:
        """
        Example string: dev_core447_MediaPlugin::Pause
        """
        try:
            return self.action_index[action_id]
        except KeyError:
            log.warning(f"Requested action {action_id} not found, skipping...")
            return None
            
    def get_plugin_by_id(self, plugin_id:str) -> PluginBase:
        plugins = self.get_plugins()
        for plugin in plugins.keys():
            _id = get_last_dir(plugins[plugin]["folder-path"])
            if _id == plugin_id:
                return plugins[plugin]["object"]
            
    def remove_plugin_from_list(self, plugin_base: PluginBase):
        del PluginBase.plugins[plugin_base.plugin_name]