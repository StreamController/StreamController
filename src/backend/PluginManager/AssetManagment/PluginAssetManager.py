"""
Author: G4PLS
Year: 2024
"""

import json
import os.path

from .PluginAssetManagerBackend import Asset, Manager
from src.backend.DeckManagement.Media.Media import Media

class Color(Asset):
    def __init__(self, *args, **kwargs):
        self._color: tuple[int, int, int, int] = (0,0,0,0)

        super().__init__(*args, **kwargs)

    def change(self, *args, **kwargs):
        self._color = kwargs.get("color", (0,0,0,0))

    def get_values(self):
        return self._color

    def to_json(self):
        return list(self._color)

    @classmethod
    def from_json(cls, *args):
        return cls(color=tuple(args[0]))

class Icon(Asset):
    def __init__(self, *args, **kwargs):
        self._icon: Media = None
        self._rendered: Media = None
        self._path: str = None

        super().__init__(*args, **kwargs)

    def change(self, *args, **kwargs):
        path = kwargs.get("path", None)

        if os.path.isfile(path):
            self._path = path
            self._icon = Media.from_path(path)
            self._rendered = self._icon.get_final_media()

    def get_values(self):
        return self._icon, self._rendered

    def to_json(self):
        return self._path

    @classmethod
    def from_json(cls, *args):
        return cls(path=args[0])

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
        os.makedirs(os.path.dirname(self.plugin_base.settings_path), exist_ok=True)

        if not os.path.isfile(self.plugin_base.settings_path):
            with open(self.plugin_base.settings_path, "w") as f:
                json.dump({}, f)

        assets = {}
        assets[self.colors.get_save_key()] = self.colors.get_override_json()
        assets[self.icons.get_save_key()] = self.icons.get_override_json()

        with open(self.plugin_base.settings_path, "r+") as f:
            try:
                content = json.load(f)
            except json.JSONDecodeError as e:
                content = {}

            content["assets"] = assets

            f.seek(0)
            json.dump(content, f, indent=4)
            f.truncate()