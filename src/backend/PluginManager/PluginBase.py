import os
import inspect
import json
import time
import Pyro5.api
import Pyro5.errors
import subprocess
from packaging import version

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
    disabled_plugins = {}
    
    def __init__(self):
        self._backend: Pyro5.api.Proxy = None

        self.PATH = os.path.dirname(inspect.getfile(self.__class__))

        self.locale_manager = LocaleManager(os.path.join(self.PATH, "locales"))
        self.locale_manager.set_to_os_default()

        self.action_holders: dict = {}

        self.registered: bool = False

    def register(self, plugin_name: str, github_repo: str, plugin_version: str, app_version: str):
        """
        Registers a plugin with the given information.

        Args:
            plugin_name (str): The name of the plugin.
            github_repo (str): The GitHub repository URL of the plugin.
            plugin_version (str): The version of the plugin.
            app_version (str): The version of the application. Do NOT set it programmatically (e.g. by using gl.app_version).

        Raises:
            ValueError: If the plugin name is not specified or if the plugin already exists.

        Returns:
            None
        """
        
        # Verify variables
        if plugin_name in ["", None]:
            log.error("Plugin: Please specify a plugin name")
            return
        if github_repo in ["", None]:
            log.error(f"Plugin: {plugin_name}: Please specify a github repo")
            return
        if plugin_name in PluginBase.plugins.keys():
            log.error(f"Plugin: {plugin_name}: Plugin already exists")
            return
        
        
        if self.do_versions_match(app_version):
            # Register plugin
            PluginBase.plugins[plugin_name] = {
                "object": self,
                "github": github_repo,
                "version": plugin_version,
                "folder-path": os.path.dirname(inspect.getfile(self.__class__)),
                "file_name": os.path.basename(inspect.getfile(self.__class__))
            }
            self.registered = True

        else:
            log.warning(
                f"Plugin {plugin_name} is not compatible with this version of StreamController. "
                f"Please update your assets! Plugin requires version {plugin_version} and you are "
                f"running version {gl.app_version}. Disabling plugin."
            )
            PluginBase.disabled_plugins[plugin_name] = {
                "object": self,
                "github": github_repo,
                "version": plugin_version,
                "folder-path": os.path.dirname(inspect.getfile(self.__class__)),
                "file_name": os.path.basename(inspect.getfile(self.__class__))
            }

        self.plugin_name = plugin_name
        self.github_repo = github_repo
        self.version = plugin_version

    def do_versions_match(self, app_version_to_check: str):
        if gl.exact_app_version_check:
            gl.app_version == app_version
            return
        
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

    def launch_backend(self, backend_path: str, venv_path: str = None, open_in_terminal: bool = False):
        uri = self.add_to_pyro()

        ## Launch
        if open_in_terminal:
            command = "gnome-terminal -- bash -c '"
            if venv_path is not None:
                command += f"source {venv_path}/bin/activate && "
            command += f"python3 {backend_path} --uri={uri}; exec $SHELL'"
        else:
            command = ""
            if venv_path is not None:
                command = f"source {venv_path}/bin/activate && "
            command += f"python3 {backend_path} --uri={uri}"

        log.info(f"Launching backend: {command}")
        subprocess.Popen(command, shell=True, start_new_session=open_in_terminal)

        self.wait_for_backend()

    def wait_for_backend(self, tries: int = 3):
        while tries > 0 and self._backend is None:
            time.sleep(0.1)
            tries -= 1

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

    def get_selector_icon(self) -> Gtk.Widget:
        return Gtk.Image(icon_name="view-paged")
    
    def on_uninstall(self) -> None:
        try:
            # Stop backend if running
            if self.backend is not None:
                self.backend.stop()
                self.backend._pyroRelease()
                self._backend = None
        except Exception as e:
            log.error(e)

    def ping(self) -> bool:
        return True