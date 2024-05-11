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

        self.generate_folder_structure("icons")

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
        path = os.path.join(self.path, manifest.get("thumbnail"))
        if os.path.exists(path):
            return path
        return None
    
    def get_icons(self) -> list[Icon]:
        return self.get_content_from_structure()

    def get_content_from_structure(self) -> list[Icon]:
        content: list[Icon] = []

        for folder_name, folder_entry in self.pack_structure.items():
            for entry in folder_entry:
                content.append(entry)

        return content

    def generate_folder_structure(self, asset_path: str):
        manifest = self.get_manifest()
        asset_path = manifest.get(asset_path)
        pack_path = os.path.join(self.path, asset_path)

        if not os.path.exists(pack_path):
            return

        # Load Content From Base Directory
        base_dir_content = self.load_content(pack_path)
        if base_dir_content:
            self.pack_structure["Base"] = base_dir_content

        # Load content from Subfolders
        subfolders = [entry for entry in os.scandir(pack_path) if entry.is_dir()]

        for folder in subfolders:
            if not self.pack_structure.__contains__(folder.name):
                self.pack_structure[folder.name] = []
            icons = self.load_content(folder.path)
            self.pack_structure[folder.name] = icons

    def load_content(self, folder_path: str):
        content: list = []

        for entry in os.scandir(folder_path):
            if os.path.isdir(entry.path):
                continue
            content.append(Icon(icon_pack=self, path=entry.path))

        return content