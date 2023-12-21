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
        # Get name from folder path by removing everything before the first "::"
        self.name = os.path.basename(path).split("::", 1)[1]

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
        icons: list[Icon] = []

        manifest = self.get_manifest()
        icons_path = manifest.get("icons")
        icons_path = os.path.join(self.path, icons_path)

        if not os.path.exists(icons_path):
            return icons

        for icon in os.listdir(icons_path):
            icons.append(Icon(icon_pack=self, path=os.path.join(icons_path, icon)))


        return icons