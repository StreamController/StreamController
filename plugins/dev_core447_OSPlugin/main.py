from src.backend.PluginManager.ActionBase import ActionBase
from src.backend.PluginManager.PluginBase import PluginBase

# Import gtk modules
import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw

import sys
import os
import webbrowser
from loguru import logger as log
from PIL import Image, ImageEnhance
import math
import threading

# Add plugin to sys.paths
sys.path.append(os.path.dirname(__file__))

class RunCommand(ActionBase):
    ACTION_NAME = "Run Command"
    CONTROLS_KEY_IMAGE = False
    def __init__(self, deck_controller, page, coords):
        super().__init__(deck_controller=deck_controller, page=page, coords=coords)

        self.set_default_image(Image.open(os.path.join(self.PLUGIN_BASE.PATH, "assets", "terminal.png")))

    def on_key_down(self):
        command = self.get_settings().get("command", None)
        self.run_command(command)

    def get_config_rows(self):
        entry_row = Adw.EntryRow(title="Command:")

        # Load from config
        settings = self.get_settings()
        command = settings.setdefault("command", None)
        if command is None:
            command = ""
        entry_row.set_text(command)
        self.set_settings(settings)

        # Connect entry
        entry_row.connect("notify::text", self.on_change_command)

        return [entry_row]

    def on_change_command(self, entry, *args):
        settings = self.get_settings()
        settings["command"] = entry.get_text()
        self.set_settings(settings)

    def run_command(self, command):
        if command is None:
            return
        if not command.endswith("&"):
            command += " &"
        os.system(command)

class OpenInBrowser(ActionBase):
    ACTION_NAME = "Open In Browser"
    CONTROLS_KEY_IMAGE = False

    def __init__(self, deck_controller, page, coords):
        super().__init__(deck_controller=deck_controller, page=page, coords=coords)
        self.set_default_image(Image.open(os.path.join(self.PLUGIN_BASE.PATH, "assets", "web.png")))

    def on_key_down(self):
        url = self.get_settings().get("url", None)
        self.open_url(url)

    def get_config_rows(self):
        entry_row = Adw.EntryRow(title="URL:")
        new_window_toggle = Adw.SwitchRow(title="Open in new window")

        # Load from config
        settings = self.get_settings()
        url = settings.setdefault("url", None)
        if url is None:
            url = ""
        entry_row.set_text(url)
        new_window_toggle.set_active(settings.setdefault("new_window", False))
        self.set_settings(settings)

        # Connect entry
        entry_row.connect("notify::text", self.on_change_url)
        # Connect switch
        new_window_toggle.connect("notify::active", self.on_change_new_window)

        return [entry_row, new_window_toggle]

    def on_change_url(self, entry, *args):
        settings = self.get_settings()
        settings["url"] = entry.get_text()
        self.set_settings(settings)

    def on_change_new_window(self, switch, *args):
        settings = self.get_settings()
        settings["new_window"] = switch.get_active()
        self.set_settings(settings)

    def open_url(self, url):
        if url in [None, ""]:
            return
        new = 1 if self.get_settings().get("new_window", False) else 0
        webbrowser.open(url, new=new)

class OSPlugin(PluginBase):
    def __init__(self):
        self.PLUGIN_NAME = "OS"
        self.GITHUB_REPO = "https://github.com/your-github-repo"
        super().__init__()
        print(self.ACTIONS)
        self.add_action(RunCommand)
        self.add_action(OpenInBrowser)
        print(self.ACTIONS)
        print()