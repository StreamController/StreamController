from src.backend.PluginManager.ActionBase import ActionBase
from src.backend.PluginManager.PluginBase import PluginBase

# Import gtk modules
import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw

import sys
import os
from loguru import logger as log
from PIL import Image, ImageEnhance
import math

# Add plugin to sys.paths
sys.path.append(os.path.dirname(__file__))

class RunCommand(ActionBase):
    ACTION_NAME = "Run Command"
    CONTROLS_KEY_IMAGE = True
    def __init__(self, deck_controller, page, coords):
        super().__init__(deck_controller=deck_controller, page=page, coords=coords)

    def on_ready(self):
        self.set_key(media_path=os.path.join(self.PLUGIN_BASE.PATH, "assets", "terminal.png"))

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


class OSPlugin(PluginBase):
    def __init__(self):
        self.PLUGIN_NAME = "OS"
        self.GITHUB_REPO = "https://github.com/your-github-repo"
        super().__init__()
        print(self.ACTIONS)
        self.add_action(RunCommand)
        print(self.ACTIONS)
        print()