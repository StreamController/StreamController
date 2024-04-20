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
from locales.LocaleManager import LocaleManager
from src.backend.PluginManager.ActionHolder import ActionHolder

class PluginBase(rpyc.Service):
    plugins = {}
    disabled_plugins = {}
    
    def __init__(self):
        self.backend_connection: Connection = None
        self.backend: netref = None
        self.server: ThreadedServer = None

        self.PATH = os.path.dirname(inspect.getfile(self.__class__))

        self.locale_manager = LocaleManager(os.path.join(self.PATH, "locales"))
        self.locale_manager.set_to_os_default()

        self.action_holders: dict = {}

        self.registered: bool = False

        self.plugin_name: str = None

    def register(self):
        """
        Registers a plugin with the given information.

        Raises:
            ValueError: If the plugin name is not specified or if the plugin already exists.

        Returns:
            None
        """

        manifest = self.get_manifest()
        plugin_name = manifest.get("plugin-name") or None
        github_repo = manifest.get("github") or None
        plugin_version = manifest.get("plugin-version") or None
        minimum_app_version = manifest.get("minimum-app-version") or None
        
        # Verify variables
        if plugin_name in ["", None]:
            log.error("Plugin: Please specify a plugin name")
            return
        if github_repo in ["", None]:
            log.error(f"Plugin: {plugin_name}: Please specify a github repo")
            return
        
        self.plugin_id = manifest.get("plugin-id")

        for plugin_id in PluginBase.plugins.keys():
            plugin = PluginBase.plugins[plugin_id]["object"]
            if plugin.plugin_name == plugin_name:
                log.error(f"Plugin: {plugin_name}: Plugin already exists")
                return

        if self.do_versions_match(manifest.get("current-app-version") or None):
            if self.do_versions_match(minimum_app_version, True):
                # Register plugin
                PluginBase.plugins[self.plugin_id] = {
                    "object": self,
                    "plugin_version": plugin_version,
                    "minimum_app_version": minimum_app_version,
                    "github": github_repo,
                    "folder_path": os.path.dirname(inspect.getfile(self.__class__)),
                    "file_name": os.path.basename(inspect.getfile(self.__class__))
                }
                self.registered = True
            else:
                log.warning(f"Plugin {self.plugin_id} is not compatible with this version of StreamController. "
                            f"Please update StreamController! Plugin requires app version {minimum_app_version} and "
                            f"you are on version {gl.app_version}. Disabling plugin.")
                PluginBase.disabled_plugins[self.plugin_id] = {
                    "object": self,
                    "plugin_version": plugin_version,
                    "minimum_app_version": minimum_app_version,
                    "github": github_repo,
                    "folder-path": os.path.dirname(inspect.getfile(self.__class__)),
                    "file_name": os.path.basename(inspect.getfile(self.__class__))
                }
        else:
            log.warning(
                f"Plugin {self.plugin_id} is not compatible with this version of StreamController. "
                f"Please update your assets! Plugin requires version {plugin_version} and you are "
                f"running version {gl.app_version}. Disabling plugin."
            )
            PluginBase.disabled_plugins[self.plugin_id] = {
                "object": self,
                "plugin_version": plugin_version,
                "minimum_app_version": minimum_app_version,
                "github": github_repo,
                "folder-path": os.path.dirname(inspect.getfile(self.__class__)),
                "file_name": os.path.basename(inspect.getfile(self.__class__))
            }

        self.plugin_name = plugin_name
        self.github_repo = github_repo
        self.plugin_version = plugin_version

    def get_plugin_id(self) -> str:
        module = importlib.import_module(self.__module__)
        subclass_file = module.__file__
        return os.path.basename(os.path.dirname(os.path.abspath(subclass_file)))

    def do_versions_match(self, app_version_to_check: str, is_min_app_version: bool = False):
        if is_min_app_version:
            if app_version_to_check is None:
                return True
            min_version = version.parse(app_version_to_check)
            app_version = version.parse(gl.app_version)

            return min_version < app_version
        #if gl.exact_app_version_check:
        #    gl.app_version == app_version
        #    return
        
        # Only compare major version
        app_version = version.parse(gl.app_version)
        app_version_to_check = version.parse(app_version_to_check)

        return app_version.major == app_version_to_check.major

    def add_action_holder(self, action_holder: ActionHolder):
        if not isinstance(action_holder, ActionHolder):
            raise ValueError("Please pass an ActionHolder")
        
        self.action_holders[action_holder.action_id] = action_holder

    def get_settings(self):
        if os.path.exists(os.path.join(self.PATH, "settings.json")):
            with open(os.path.join(self.PATH, "settings.json"), "r") as f:
                return json.load(f)
        return {}

    def get_manifest(self):
        if os.path.exists(os.path.join(self.PATH, "manifest.json")):
            with open(os.path.join(self.PATH, "manifest.json"), "r") as f:
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

    def get_selector_icon(self) -> Gtk.Widget:
        return Gtk.Image(icon_name="view-paged")
    
    def on_uninstall(self) -> None:
        try:
            # Stop backend if running
            if self.backend is not None:
                self.on_disconnect(self.backend_connection)
        except Exception as e:
            log.error(e)

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