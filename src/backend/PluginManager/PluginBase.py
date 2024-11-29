from functools import lru_cache
import importlib
import os
import inspect
import json
import threading
import time
import subprocess
from packaging import version

from loguru import logger as log

import rpyc
from rpyc.utils.server import ThreadedServer
from rpyc.core.protocol import Connection
from rpyc.core import netref

# Import gtk modules
import gi

from locales.LocaleManager import LocaleManager
from src.backend.PluginManager.PluginSettings.Asset import Icon, Color
from src.backend.PluginManager.PluginSettings.PluginAssetManager import AssetManager

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, Gdk

# Import globals
import globals as gl

# Import own modules
from locales.LegacyLocaleManager import LegacyLocaleManager
from src.backend.PluginManager.ActionHolder import ActionHolder
from src.backend.PluginManager.EventHolder import EventHolder

class PluginBase(rpyc.Service):
    """
    The base class for all plugins.
    """

    plugins = {}
    disabled_plugins = {}

    def __init__(self, use_legacy_locale: bool = True, legacy_dir: str = "locales"):
        self.backend_connection: Connection = None
        self.backend: netref = None
        self.server: ThreadedServer = None

        self.PATH = os.path.dirname(inspect.getfile(self.__class__))
        self.settings_path: str = os.path.join(gl.DATA_PATH, "settings", "plugins", self.get_plugin_id_from_folder_name(), "settings.json") #TODO: Retrive from the manifest as well

        if use_legacy_locale:
            self.locale_manager = LegacyLocaleManager(os.path.join(self.PATH, legacy_dir))
        else:
            self.locale_manager = LocaleManager(os.path.join(self.PATH, "locales.csv"))
        self.locale_manager.set_to_os_default()

        self.action_holders: dict = {}

        self.event_holders: dict = {}

        self.registered: bool = False

        self.plugin_name: str = None

        self.asset_manager: AssetManager = AssetManager(self)
        self.asset_manager.load_assets()

        self.has_plugin_settings: bool = False
        self.first_setup: bool = True

        self.registered_pages: list[str] = []

    @lru_cache(maxsize=1)
    def get_plugin_id(self) -> str:
        """
        Retrieves the plugin ID from the manifest. If the ID is not found, it falls back to getting the plugin ID from the folder name.
        
        The function uses the `lru_cache` decorator to cache the result of the function. The cache size is set to 1, meaning that only the most recent result is stored.
        
        Returns:
            str: The plugin ID.
        """
        manifest = self.get_manifest()
        return manifest.get("id") or self.get_plugin_id_from_folder_name()

    def register(self, plugin_name: str = None, github_repo: str = None, plugin_version: str = None,
                 app_version: str = None):
        """
        Registers a plugin with the given information.

        Args:
            plugin_name (str, optional): The name of the plugin. Defaults to None.
            github_repo (str, optional): The GitHub repository of the plugin. Defaults to None.
            plugin_version (str, optional): The version of the plugin. Defaults to None.
            app_version (str, optional): The version of StreamController. Defaults to None.

        Raises:
            ValueError: If the plugin name is not specified or if the plugin already exists.

        Returns:
            None
        """

        manifest = self.get_manifest()
        self.plugin_name = plugin_name or manifest.get("name") or None
        self.github_repo = github_repo or manifest.get("github") or None
        self.plugin_version = plugin_version or manifest.get("version") or None
        self.min_app_version = manifest.get("minimum-app-version")
        self.app_version = app_version or manifest.get("app-version")
        self.plugin_id = self.get_plugin_id()

        # Verify variables
        if self.plugin_name in ["", None]:
            log.error("Plugin: Please specify a plugin name")
            return
        if self.plugin_id in ["", None]:
            log.error(f"Plugin: {self.plugin_name}: Please specify a plugin id")
            return
        if self.github_repo in ["", None]:
            log.error(f"Plugin: {self.plugin_name}: Please specify a github repo")
            return
        if self.plugin_version in ["", None]:
            log.error(f"Plugin: {self.plugin_name}: Please specify a plugin version")
            return
        if self.app_version in ["", None]:
            log.error(f"Plugin: {self.plugin_name}: Please specify a app version")
            return


        for plugin_id in PluginBase.plugins.keys():
            plugin = PluginBase.plugins[plugin_id]["object"]
            if plugin.plugin_name == self.plugin_name:
                log.error(f"Plugin: {self.plugin_name}: Plugin already exists")
                return
            
        if self.is_app_version_matching():
            # Register plugin
            PluginBase.plugins[self.plugin_id] = {
                "object": self,
                "plugin_version": self.plugin_version,
                "minimum_app_version": self.min_app_version,
                "github": self.github_repo,
                "folder_path": os.path.dirname(inspect.getfile(self.__class__)),
                "file_name": os.path.basename(inspect.getfile(self.__class__))
            }
            self.registered = True

            settings = self.get_settings()
            self.first_setup = settings.get("first-setup", True)
        else:
            reason = None

            if self._get_parsed_base_version(self.min_app_version) > self._get_parsed_base_version(gl.app_version):
                # Plugin is too new - StreamController is too old
                log.warning(
                    f"Plugin {self.plugin_id} is not compatible with this version of StreamController. "
                    f"Please update StreamController! Plugin requires app version {self.min_app_version} "
                    f"you are running version {gl.app_version}. Disabling plugin."
                )
                reason = "app-out-of-date"

            elif version.parse(self.app_version).major != version.parse(gl.app_version).major:
                # Plugin is too old - StreamController is too new
                max_version = f"{version.parse(self.app_version).major}.x.x"
                log.warning(
                    f"Plugin {self.plugin_id} is not compatible with this version of StreamController. "
                    f"Please update your assets! Plugin requires an app version between {self.min_app_version} and {max_version} "
                    f"you are running version {gl.app_version}. Disabling plugin."
                )
                reason = "plugin-out-of-date"

            PluginBase.disabled_plugins[self.plugin_id] = {
                "object": self,
                "plugin_version": self.plugin_version,
                "minimum_app_version": self.min_app_version,
                "github": self.github_repo,
                "folder_path": os.path.dirname(inspect.getfile(self.__class__)),
                "file_name": os.path.basename(inspect.getfile(self.__class__)),
                "reason": reason
            }

    def _get_parsed_base_version(self, version_str: str) -> version.Version:
        """
        Parses a version string and returns the base version.

        Args:
            version_str (str): The version string to parse.

        Returns:
            version.Version: The parsed base version.

        Raises:
            None.
        """
        if version_str is None:
            return
        base_version = version.parse(version_str).base_version
        return version.parse(base_version)

    def get_plugin_id_from_folder_name(self) -> str:
        """
        Retrieves the plugin ID from the folder name of the subclass file.
        Returns:
            str: The plugin ID extracted from the folder name.
        """
        module = importlib.import_module(self.__module__)
        subclass_file = module.__file__
        return os.path.basename(os.path.dirname(os.path.abspath(subclass_file)))
    
    def is_minimum_version_ok(self) -> bool:
        """
        Check if the minimum required version of the application is met.

        Returns:
            bool: True if the minimum version is met, False otherwise.
        """
        if self.min_app_version is None:
            return True
        
        app_version = self._get_parsed_base_version(gl.app_version)
        min_app_version = self._get_parsed_base_version(self.min_app_version)

        return app_version >= min_app_version

    def are_major_versions_matching(self) -> bool:
        """
        Check if the major versions of the application and the plugin are matching.

        Returns:
            bool: True if the major versions are matching, False otherwise.
        """
        app_version = version.parse(gl.app_version)
        # Should use the current app version the plugin uses instead of the minimum app version
        current_app_version = version.parse(self.app_version)

        return app_version.major == current_app_version.major

    #TODO: BETTER ERROR HANDLING FOR are_major_versions_matching and is_minimum_version_ok
    def is_app_version_matching(self) -> bool:
        """
        Check if the application version matches the minimum required version for this plugin.

        Returns:
            bool: True if the application version is compatible with the plugin, False otherwise.
        """
        return self.are_major_versions_matching() and self.is_minimum_version_ok()

    def add_action_holder(self, action_holder: ActionHolder):
        """
        Adds an action holder to the plugin.

        Args:
            action_holder (ActionHolder): The action holder to be added.

        Raises:
            ValueError: If action_holder is not an instance of ActionHolder.

        Returns:
            None
        """
        if not isinstance(action_holder, ActionHolder):
            raise ValueError("Please pass an ActionHolder")
        
        if not action_holder.get_is_compatible():
            return
        
        self.action_holders[action_holder.action_id] = action_holder

    def add_event_holder(self, event_holder: EventHolder) -> None:
        """
        Adds a EventHolder to the Plugin

        Args:
            event_holder (EventHolder): The Event Holder

        Raises:
            ValueError: If the event holder is not an EventHolder

        Returns:
            None
        """
        if not isinstance(event_holder, EventHolder):
            raise ValueError("Please pass an SignalHolder")

        self.event_holders[event_holder.event_id] = event_holder

    def connect_to_event(self, event_id: str, callback: callable) -> None:
        """
        Connects a Callback to the Event which gets specified by the event ID

        Args:
            event_id (str): The ID of the Event.
            callback (callable): The Callback that gets Called when the Event triggers

        Returns:
            None
        """
        if event_id in self.event_holders:
            self.event_holders[event_id].add_listener(callback)
        else:
            log.warning(f"{event_id} does not exist in {self.plugin_name}")

    def connect_to_event_directly(self, plugin_id: str, event_id: str, callback: callable) -> None:
        """
        Connects a Callback directly to a Plugin with the specified ID

        Args:
            plugin_id (str): The ID of the Plugin
            event_id (str): The ID of the Event
            callback (callable): The Callback that gets Called when the Event triggers

        Returns:
            None
        """
        plugin = self.get_plugin(plugin_id)
        if plugin is None:
            log.warning(f"{plugin_id} does not exist")
        else:
            plugin.connect_to_event(event_id, callback)

    def disconnect_from_event(self, event_id: str, callback: callable) -> None:
        """
        Disconnects a Callback from the Event which gets specified by the event ID

        Args:
            event_id (str): The ID of the Event.
            callback (callable): The Callback that gets Removed

        Returns:
            None
        """
        if event_id in self.event_holders:
            self.event_holders[event_id].remove_listener(callback)
        else:
            log.warning(f"{event_id} does not exist in {self.plugin_name}")

    def disconnect_from_event_directly(self, plugin_id: str, event_id: str, callback: callable) -> None:
        """
        Disconnects a Callback directly from a plugin with the specified ID

        Args:
            plugin_id (str): The ID of the Plugin
            event_id (str): The ID of the Event.
            callback (callable): The Callback that gets Removed

        Returns:
            None
        """
        plugin = self.get_plugin(plugin_id)
        if plugin is None:
            log.warning(f"{plugin_id} does not exist")
        else:
            self.disconnect_from_event(event_id, callback)

    def get_settings(self):
        """
        Retrieves the settings from the settings file.

        Returns:
            dict: The settings stored in the settings file. If the settings file does not exist, an empty dictionary is returned.
        """
        if not os.path.exists(self.settings_path):
            return {}
        with open(self.settings_path, "r") as f:
            settings = json.load(f)
            settings = settings.get("settings", {})
            return settings

    def get_manifest(self):
        """
        Retrieves the content of the manifest file from the plugin's directory if it exists.

        Returns:
            dict: The contents of the manifest file as a dictionary, or an empty dictionary if the file does not exist.
        """
        if os.path.exists(os.path.join(self.PATH, "manifest.json")):
            with open(os.path.join(self.PATH, "manifest.json"), "r") as f:
                return json.load(f)
        return {}

    def get_about(self):
        """
        Retrieves the content from the about file from the plugin's directory if it exists.

         Returns:
            dict: The contents of the about file as a dictionary, or an empty dictionary if the file does not exist.
        """

        if os.path.exists(os.path.join(self.PATH, "about.json")):
            with open(os.path.join(self.PATH, "about.json"), "r") as f:
                return json.load(f)
        return {}
    
    def set_settings(self, settings):
        """
        Saves the provided settings to the settings file.

        Args:
            settings (dict): The settings to be saved.

        Returns:
            None
        """
        os.makedirs(os.path.dirname(self.settings_path), exist_ok=True)

        if not os.path.isfile(self.settings_path):
            with open(self.settings_path, "w") as f:
                json.dump({}, f)

        with open(self.settings_path, "r+") as f:
            content = json.load(f)
            content["settings"] = settings
            f.seek(0)
            json.dump(content, f, indent=4)
            f.truncate()

    def add_css_stylesheet(self, path):
        """
        Adds a CSS stylesheet to the application's style context.

        Args:
            path (str): The path to the CSS file.

        Returns:
            None
        """
        css_provider = Gtk.CssProvider()
        css_provider.load_from_path(path)
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(),
            css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

    def register_page(self, path: str) -> None:
        """
        Registers a page for this plugin that will be shown in the ui.

        Args:
            path (str): The path of the page to be registered.

        Returns:
            None
        """
        gl.page_manager.register_page(path)
        self.registered_pages.append(path)

    def get_selector_icon(self) -> Gtk.Widget:
        """
        Returns a Gtk.Image widget with the icon "view-paged".

        Returns:
            Gtk.Widget: A Gtk.Image widget.
        """

        return Gtk.Image(icon_name="view-paged")
    
    def on_uninstall(self) -> None:
        """
        Unregisters the plugin pages and stops the backend connection if running.

        This method is called when the plugin is being uninstalled. It ensures that any pages registered
        by the plugin are unregistered and the backend connection is stopped properly.
        
        Returns:
            None
        """ 
        for page in self.registered_pages:
            gl.page_manager.unregister_page(page)
        try:
            # Stop backend if running
            if self.backend is not None:
                self.on_disconnect(self.backend_connection)
        except Exception as e:
            log.error(e)

    def get_plugin(self, plugin_id: str) -> "PluginBase":
        """
        Retrieves a plugin by its ID.

        Args:
            plugin_id (str): The ID of the plugin to retrieve.

        Returns:
            PluginBase: The plugin object if found, otherwise None.
        """
        return gl.plugin_manager.get_plugin_by_id(plugin_id) or None

    # Asset Management

    def add_icon(self, key: str, path: str):
        self.asset_manager.icons.add_asset(key=key, asset=Icon(path=path))

    def add_color(self, key: str, color: tuple[int, int, int, int]):
        self.asset_manager.colors.add_asset(key=key, asset=Color(color=color))

    def get_asset_path(self, asset_name: str, subdirs: list[str] = None, asset_folder: str = "assets") -> str:
        """
        Helper method that returns paths to plugin assets.

        Args:
            asset_name (str): Name of the Asset File
            subdirs (list[str], optional): Subdirectories. Defaults to [].
            asset_folder (str, optional): Name of the folder where assets are stored. Defaults to "assets".

        Returns:
            str: The full path to the asset
        """

        if not subdirs:
            return os.path.join(self.PATH, asset_folder, asset_name)

        subdir = os.path.join(*subdirs)
        if subdir != "":
            return os.path.join(self.PATH, asset_folder, subdir, asset_name)
        return ""

    def get_settings_area(self):
        pass

    # ---------- #
    # Rpyc stuff #
    # ---------- #

    def start_server(self) -> None:
        """
        Starts the RPyC server for the plugin.

        This method initializes and starts a ThreadedServer to allow remote procedure calls (RPC)
        for the plugin. If the server is already running, it logs a warning and skips starting a new server.

        Returns:
            None
        """
        if self.server is not None:
            log.warning("Server already running, skipping...")
            return
        self.server = ThreadedServer(self, hostname="localhost", port=0, protocol_config={"allow_public_attrs": True})
        threading.Thread(target=self.server.start, name="server_start", daemon=True).start()

    def on_disconnect(self, conn: Connection) -> None:
        """
        Handles the disconnection of the RPyC server.

        This method closes the RPyC server and the backend connection if they are running.

        Args:
            conn (Connection): The connection object to be disconnected.

        Returns:
            None
        """
        if self.server is not None:
            self.server.close()
        if self.backend_connection is not None:
            self.backend_connection.close()
        self.backend_connection = None

    def launch_backend(self, backend_path: str, venv_path: str = None, open_in_terminal: bool = False) -> None:
        """
        Launches the backend process for the plugin.

        This method starts the RPyC server, constructs the command to launch the backend script,
        and runs it in a new subprocess. Optionally, the backend can be launched in a new terminal window.

        Args:
            backend_path (str): The path to the backend script to be executed.
            venv_path (str, optional): The path to the virtual environment to activate. Defaults to None.
            open_in_terminal (bool, optional): Whether to open the backend in a new terminal window. Defaults to False.

        Returns:
            None
        """
        self.start_server()
        port = self.server.port

        # Construct the command to launch the backend
        if open_in_terminal:
            command = "gnome-terminal -- bash -c '"
            if venv_path is not None:
                command += f". {venv_path}/bin/activate && "
            command += f"python3 {backend_path} --port={port}; exec $SHELL'"
        else:
            command = ""
            if venv_path is not None:
                command = f". {venv_path}/bin/activate && "
            command += f"python3 {backend_path} --port={port}"

        log.info(f"Launching backend: {command}")
        subprocess.Popen(command, shell=True, start_new_session=open_in_terminal)

        self.wait_for_backend()

    def wait_for_backend(self, tries: int = 3) -> None:
        """
        Waits for the backend to establish a connection.

        This method repeatedly checks if the backend connection is established within the given number of tries.

        Args:
            tries (int, optional): The number of attempts to wait for the backend connection. Defaults to 3.

        Returns:
            None
        """
        while tries > 0 and self.backend_connection is None:
            time.sleep(0.1)
            tries -= 1

    def register_backend(self, port: int) -> None:
        """
        Registers the backend connection for the plugin.

        This is an internal method and should not be called manually. It connects to the backend using
        the specified port and adds the backend connection to the global plugin manager.

        Args:
            port (int): The port number to connect to the backend.

        Returns:
            None
        """
        self.backend_connection = rpyc.connect("localhost", port)
        self.backend = self.backend_connection.root
        gl.plugin_manager.backends.append(self.backend_connection)

    def ping(self) -> bool:
        """
        A simple method to check the availability of the plugin.

        Returns:
            bool: Always returns True.
        """
        return True

    def request_dbus_permission(self, name: str, bus: str = "session", description: str = None) -> None:
        """
        Requests DBus permission for the plugin.

        This method shows a dialog requesting DBus permission for the specified bus with the given name
        and description. If no description is provided, a default description is used.

        Args:
            name (str): The name of the bus.
            bus (str, optional): The type of bus, either "session" or "system". Defaults to "session".
            description (str, optional): The description of why the permission is needed. Defaults to None.

        Raises:
            ValueError: If the plugin is not registered before requesting permissions.

        Returns:
            None
        """
        if description is None:
            description = gl.lm.get("permissions.request.plugin-blueprint")
            if self.plugin_name is None:
                raise ValueError("Register the plugin before requesting permissions")
            description = description.replace("{name}", self.plugin_name)
        gl.flatpak_permission_manager.show_dbus_permission_request_dialog(name, bus, description)

    def get_config_rows(self) -> list[Adw.PreferencesRow]:
        return []