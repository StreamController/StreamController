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
    plugins = {}
    disabled_plugins = {}
    
    def __init__(self):
        self.backend_connection: Connection = None
        self.backend: netref = None
        self.server: ThreadedServer = None

        self.PATH = os.path.dirname(inspect.getfile(self.__class__))
        self.settings_path: str = os.path.join(gl.DATA_PATH, "settings", "plugins", self.get_plugin_id_from_folder_name(), "settings.json") #TODO: Retrive from the manifest as well

        self.locale_manager = LegacyLocaleManager(os.path.join(self.PATH, "locales"))
        self.locale_manager.set_to_os_default()

        self.action_holders: dict = {}

        self.event_holders: dict = {}

        self.registered: bool = False

        self.plugin_name: str = None

        self.registered_pages: list[str] = []

    def register(self, plugin_name: str = None, github_repo: str = None, plugin_version: str = None,
                 app_version: str = None):
        """
        Registers a plugin with the given information.

        Raises:
            ValueError: If the plugin name is not specified or if the plugin already exists.

        Returns:
            None
        """

        manifest = self.get_manifest()
        self.plugin_name = plugin_name or manifest.get("name") or None
        self.github_repo = github_repo or manifest.get("github") or None
        self.plugin_version = plugin_version or manifest.get("version") or None
        self.min_app_version = manifest.get("minimum-app-version") or "0.0.0" #TODO: IMPLEMENT BETTER WAY OF VERSION ERROR HANDLING
        self.app_version = app_version or manifest.get("app-version") or "0.0.0"

        # Verify variables
        if self.plugin_name in ["", None]:
            log.error("Plugin: Please specify a plugin name")
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

        self.plugin_id = manifest.get("id") or self.get_plugin_id_from_folder_name()

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
        base_version = version.parse(version_str).base_version
        return version.parse(base_version)

    def get_plugin_id_from_folder_name(self) -> str:
        module = importlib.import_module(self.__module__)
        subclass_file = module.__file__
        return os.path.basename(os.path.dirname(os.path.abspath(subclass_file)))
    
    def is_minimum_version_ok(self) -> bool:
        app_version = self._get_parsed_base_version(gl.app_version)
        min_app_version = self._get_parsed_base_version(self.min_app_version)

        return app_version >= min_app_version

    def are_major_versions_matching(self) -> bool:
        app_version = version.parse(gl.app_version)
        # Should use the current app version the plugin uses instead of the minimum app version
        current_app_version = version.parse(self.app_version)

        return app_version.major == current_app_version.major

    #TODO: BETTER ERROR HANDLING FOR are_major_versions_matching and is_minimum_version_ok
    def is_app_version_matching(self) -> bool:
        return self.are_major_versions_matching() and self.is_minimum_version_ok()


    def add_action_holder(self, action_holder: ActionHolder):
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
        if not os.path.exists(self.settings_path):
            return {}
        with open(self.settings_path, "r") as f:
            return json.load(f)

    def get_manifest(self):
        if os.path.exists(os.path.join(self.PATH, "manifest.json")):
            with open(os.path.join(self.PATH, "manifest.json"), "r") as f:
                return json.load(f)
        return {}
    
    def set_settings(self, settings):
        os.makedirs(os.path.dirname(self.settings_path), exist_ok=True)
        with open(self.settings_path, "w") as f:
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
        self.registered_pages.append(path)

    def get_selector_icon(self) -> Gtk.Widget:
        return Gtk.Image(icon_name="view-paged")
    
    def on_uninstall(self) -> None:
        for page in self.registered_pages:
            gl.page_manager.unregister_page(page)
        try:
            # Stop backend if running
            if self.backend is not None:
                self.on_disconnect(self.backend_connection)
        except Exception as e:
            log.error(e)

    def get_plugin(self, plugin_id: str) -> "PluginBase":
        return gl.plugin_manager.get_plugin_by_id(plugin_id) or None

    # ---------- #
    # Rpyc stuff #
    # ---------- #

    def start_server(self):
        if self.server is not None:
            log.warning("Server already running, skipping...")
            return
        self.server = ThreadedServer(self, hostname="localhost", port=0, protocol_config={"allow_public_attrs": True})
        # self.server.start()
        threading.Thread(target=self.server.start, name="server_start", daemon=True).start()

    def on_disconnect(self, conn):
        if self.server is not None:
            self.server.close()
        if self.backend_connection is not None:
            self.backend_connection.close()
        self.backend_connection = None

    def launch_backend(self, backend_path: str, venv_path: str = None, open_in_terminal: bool = False):
        self.start_server()
        port = self.server.port

        ## Launch
        if open_in_terminal:
            command = "gnome-terminal -- bash -c '"
            if venv_path is not None:
                command += f"source {venv_path}/bin/activate && "
            command += f"python3 {backend_path} --port={port}; exec $SHELL'"
        else:
            command = ""
            if venv_path is not None:
                command = f"source {venv_path}/bin/activate && "
            command += f"python3 {backend_path} --port={port}"

        log.info(f"Launching backend: {command}")
        subprocess.Popen(command, shell=True, start_new_session=open_in_terminal)

        self.wait_for_backend()

    def wait_for_backend(self, tries: int = 3):
        while tries > 0 and self.backend_connection is None:
            time.sleep(0.1)
            tries -= 1

    def register_backend(self, port: int):
        """
        Internal method, do not call manually
        """
        self.backend_connection = rpyc.connect("localhost", port)
        self.backend = self.backend_connection.root
        gl.plugin_manager.backends.append(self.backend_connection)

    def ping(self) -> bool:
        return True
    
    def request_dbus_permission(self, name: str, bus: str="session", description: str = None) -> None:
        """
        name: The name of the bus
        bus: The bus type session or system
        description: Describe why you need the permission - automatically added if not provided
        """
        if description is None:
            description = gl.lm.get("permissions.request.plugin-blueprint")
            if self.plugin_name is None:
                raise ("Register the plugin before requesting permissions")
            description = description.replace("{name}", self.plugin_name)
        gl.flatpak_permission_manager.show_dbus_permission_request_dialog(name, bus, description)