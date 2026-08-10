"""
Author: G4PLS
Year: 2024
"""

import json
import os.path

from .Manager import Manager
from .Asset import Color, Icon
from src.backend.Utils.AtomicSaveUtils import atomic_save_json


class AssetManager:
    def __init__(self, plugin_base: "PluginBase"):
        self.plugin_base = plugin_base
        self.colors = Manager(Color, "colors")
        self.icons = Manager(Icon, "icons")

    def load_assets(self):
        if not os.path.exists(self.plugin_base.settings_path):
            return {}

        with open(self.plugin_base.settings_path, "r") as f:
            assets = json.load(f)
            assets = assets.get("assets", {})
            self.icons.load_json(assets)
            self.colors.load_json(assets)

    def save_assets(self):
        content = {}
        if os.path.isfile(self.plugin_base.settings_path):
            with open(self.plugin_base.settings_path, "r") as f:
                try:
                    content = json.load(f)
                except json.JSONDecodeError as e:
                    content = {}

        assets = {}
        assets[self.colors.get_save_key()] = self.colors.get_override_json()
        assets[self.icons.get_save_key()] = self.icons.get_override_json()

        content["assets"] = assets

        atomic_save_json(self.plugin_base.settings_path, content, indent=4)