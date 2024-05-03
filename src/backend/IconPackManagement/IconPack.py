"""
Author: Core447
Year: 2023

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
any later version.

This programm comes with ABSOLUTELY NO WARRANTY!

You should have received a copy of the GNU General Public License
along with this program. If not, see <https://www.gnu.org/licenses/>.
"""

import os
import json
from functools import lru_cache

# Import own modules
from src.backend.IconPackManagement.Icon import Icon

class IconPack:
    def __init__(self, path: str):
        self.path = path
        self.name = self.get_manifest().get("name") or os.path.basename(path)
        self.pack_structure: dict[str, list[Icon]] = {}

    @lru_cache(maxsize=None)
    def get_manifest(self):
        manifest_path = os.path.join(self.path, "manifest.json")
        return self.get_json(manifest_path)
        
    @lru_cache(maxsize=None)
    def get_attribution_json(self):
        attribution_path = os.path.join(self.path, "attribution.json")
        return self.get_json(attribution_path)
    
    @lru_cache(maxsize=None)
    def get_pack_attribution(self):
        attribution = self.get_attribution_json()
        return attribution.get("default", attribution.get("general", attribution.get("generic", {})))
        
    @lru_cache(maxsize=None)
    def get_json(self, json_path: str):
        if not os.path.exists(json_path):
            return {}
        
        with open(json_path) as f:
            return json.load(f)

    @lru_cache(maxsize=None)
    def get_thumbnail_path(self):
        manifest = self.get_manifest()
        path =  os.path.join(self.path, manifest.get("thumbnail"))
        if os.path.exists(path):
            return path
        return None
    
    def get_icons(self) -> list[Icon]:
        manifest = self.get_manifest()
        icons_path = manifest.get("icons")
        icon_pack_path = os.path.join(self.path, icons_path)

        if not os.path.exists(icon_pack_path):
            return []

        self.load_folder_structure(icon_pack_path)

        base_dir_icons: list[Icon] = self.load_icons(icon_pack_path)

        if base_dir_icons:
            self.pack_structure["Base"] = base_dir_icons

        return self.get_icons_from_structure()

    def get_icons_from_structure(self) -> list[Icon]:
        icons: list[Icon] = []

        for folder_name, folder_icons in self.pack_structure.items():
            for icon in folder_icons:
                icons.append(icon)

        return icons

    def load_folder_structure(self, icon_pack_path: str):
        subfolders = [entry for entry in os.scandir(icon_pack_path) if entry.is_dir()]

        for folder in subfolders:
            if not self.pack_structure.__contains__(folder.name):
                self.pack_structure[folder.name] = []
            icons = self.load_icons(folder.path)
            self.pack_structure[folder.name] = icons

    def load_icons(self, path: str) -> list[Icon]:
        icons: list[Icon] = []

        for icon in os.scandir(path):
            if os.path.isdir(icon.path):
                continue
            icons.append(Icon(icon_pack=self, path=icon.path))

        return icons