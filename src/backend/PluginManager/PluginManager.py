import os
import importlib
import sys
import re
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
        self.loaded_plugin_ids: set[str] = set()
        self._action_index_lock = threading.RLock()
        self._deferred_services_lock = threading.Lock()
        self._plugin_folder_resolution_cache: dict[str, str | None] = {}
        self._daemon_only_mode = gl.argparser.parse_args().daemon_only

    @staticmethod
    def _normalize_plugin_identifier(value: str) -> str:
        if not isinstance(value, str):
            return ""
        return re.sub(r"[^a-z0-9]+", "", value.lower())

    def _resolve_plugin_folder_id(self, plugin_id: str) -> str | None:
        if not plugin_id:
            return None
        if plugin_id in self._plugin_folder_resolution_cache:
            return self._plugin_folder_resolution_cache[plugin_id]
        if os.path.isdir(os.path.join(gl.PLUGIN_DIR, plugin_id)):
            self._plugin_folder_resolution_cache[plugin_id] = plugin_id
            return plugin_id

        normalized_target = self._normalize_plugin_identifier(plugin_id)
        if not normalized_target:
            self._plugin_folder_resolution_cache[plugin_id] = None
            return None

        try:
            folders = os.listdir(gl.PLUGIN_DIR)
        except Exception:
            return plugin_id

        matches = [
            folder for folder in folders
            if self._normalize_plugin_identifier(folder) == normalized_target
        ]
        if len(matches) == 1:
            log.debug(f"Resolved action plugin id '{plugin_id}' to plugin folder '{matches[0]}'")
            self._plugin_folder_resolution_cache[plugin_id] = matches[0]
            return matches[0]

        return plugin_id

    def _ensure_deferred_services_for_daemon_plugin_load(self) -> None:
        if not self._daemon_only_mode:
            return

        with self._deferred_services_lock:
            if (
                gl.asset_manager_backend is not None and
                gl.icon_pack_manager is not None and
                gl.wallpaper_pack_manager is not None and
                gl.sd_plus_bar_wallpaper_pack_manager is not None and
                gl.store_backend is not None
            ):
                return

            # Some plugins assume these managers exist during plugin init. In
            # daemon-only mode they are intentionally deferred, so initialize them
            # lazily when we first need to load a plugin on demand.
            from src.backend.AssetManagerBackend import AssetManagerBackend
            from src.backend.IconPackManagement.IconPackManager import IconPackManager
            from src.backend.WallpaperPackManagement.WallpaperPackManager import WallpaperPackManager
            from src.backend.SDPlusBarWallpaperPackManagement.SDPlusBarWallpaperPackManager import SDPlusBarWallpaperPackManager
            from src.backend.Store.StoreBackend import StoreBackend

            if gl.asset_manager_backend is None:
                gl.asset_manager_backend = AssetManagerBackend()
            if gl.icon_pack_manager is None:
                gl.icon_pack_manager = IconPackManager()
            if gl.wallpaper_pack_manager is None:
                gl.wallpaper_pack_manager = WallpaperPackManager()
            if gl.sd_plus_bar_wallpaper_pack_manager is None:
                gl.sd_plus_bar_wallpaper_pack_manager = SDPlusBarWallpaperPackManager()
            if gl.store_backend is None:
                gl.store_backend = StoreBackend()

    def load_plugins(self, show_notification: bool = False, plugin_ids: set[str] | None = None):
        # get all folders in plugins folder
        if not os.path.exists(gl.PLUGIN_DIR):
            os.mkdir(gl.PLUGIN_DIR)
        folders = os.listdir(gl.PLUGIN_DIR)
        for folder in folders:
            if plugin_ids is not None and folder not in plugin_ids:
                continue
            # Import main module
            import_string = f"plugins.{folder}.main"
            if import_string not in sys.modules.keys():
                # Import module only if it's not already imported
                try:
                    importlib.import_module(f"plugins.{folder}.main")
                    self.loaded_plugin_ids.add(folder)
                except Exception as e:
                    log.error(f"Error importing plugin {folder}: {e}")
            else:
                self.loaded_plugin_ids.add(folder)

        # Get all classes inheriting from PluginBase and generate objects for them
        self.init_plugins()

        if show_notification:
            self.show_n_disabled_plugins_notification()

    def show_n_disabled_plugins_notification(self):
        n_deactivated_plugins = len(PluginBase.disabled_plugins)
        if n_deactivated_plugins == 0:
            return
        
        body = f"{n_deactivated_plugins} plugins have been disabled because they are no longer compatible with the current app version"
        if n_deactivated_plugins == 1:
            body = f"{n_deactivated_plugins} plugin has been disabled because it is no longer compatible with the current app version"
        
        call = lambda: gl.app.send_notification(
            "dialog-information-symbolic",
            "Plugins",
            body,
            button=("Update All", "app.update-all-assets", None)
        )
        if gl.app is None:
            gl.app_loading_finished_tasks.append(call)
        else:
            call()

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
        with self._action_index_lock:
            self.action_index.clear()
            plugins = self.get_plugins()
            for plugin in plugins.values():
                plugin_base = plugin["object"]
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

    def get_plugins(self, include_disabled: bool = False) -> list[PluginBase]:
        plugins = PluginBase.plugins

        if include_disabled:
            plugins.update(PluginBase.disabled_plugins)

        return plugins
    
    def get_actions_for_plugin_id(self, plugin_id: str):
        return PluginBase.plugins[plugin_id]["object"].ACTIONS
    
    def get_action_holder_from_id(self, action_id: str) -> ActionHolder:
        """
        Example string: dev_core447_MediaPlugin::Pause
        """
        try:
            with self._action_index_lock:
                return self.action_index[action_id]
        except KeyError:
            log.warning(f"Requested action {action_id} not found, skipping...")
            return None

    def ensure_action_holder_loaded(self, action_id: str) -> ActionHolder | None:
        """Return an action holder, lazily loading its plugin when needed.

        This is primarily used in daemon-only mode where plugin loading may be
        deferred and a page references an action from a plugin that has not been
        loaded yet.
        """
        with self._action_index_lock:
            action_holder = self.action_index.get(action_id)
            if action_holder is not None:
                return action_holder

        plugin_id = self.get_plugin_id_from_action_id(action_id)
        if not plugin_id:
            return None
        plugin_folder_id = self._resolve_plugin_folder_id(plugin_id)
        self._ensure_deferred_services_for_daemon_plugin_load()

        with self._action_index_lock:
            action_holder = self.action_index.get(action_id)
            if action_holder is not None:
                return action_holder

            if plugin_folder_id:
                self.load_plugins(plugin_ids={plugin_folder_id})
            else:
                self.load_plugins(plugin_ids={plugin_id})
            self.generate_action_index()
            return self.action_index.get(action_id)
            
    def get_plugin_by_id(self, plugin_id:str, include_disabled: bool = True) -> PluginBase:
        return self.get_plugins(include_disabled).get(plugin_id, {}).get("object", None)
            
    def remove_plugin_from_list(self, plugin_base: PluginBase):
        del PluginBase.plugins[plugin_base.plugin_id]

    def get_plugin_id_from_action_id(self, action_id: str) -> str:
        if action_id is None:
            return
        
        return action_id.split("::")[0]
    
    def get_is_plugin_out_of_date(self, plugin_id: str) -> bool:
        plugin = PluginBase.disabled_plugins.get(plugin_id)
        if plugin is None:
            # Not installed
            return False
        
        reason = PluginBase.disabled_plugins[plugin_id].get("reason")
        return reason == "plugin-out-of-date"
