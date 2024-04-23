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
from src.backend.WallpaperPackManagement.Wallpaper import Wallpaper

class WallpaperPack:
    def __init__(self, path: str):
        self.path = path
        self.name = self.get_manifest().get("name") or os.path.basename(path)

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
    
    def get_wallpapers(self) -> list[Wallpaper]:
        wallpapers: list[Wallpaper] = []

        manifest = self.get_manifest()
        wallpapers_path = manifest.get("images")
        
        if wallpapers_path is None:
            return wallpapers
        
        wallpapers_path = os.path.join(self.path, wallpapers_path)

        if not os.path.exists(wallpapers_path):
            return wallpapers

        for wallpaper in os.listdir(wallpapers_path):
            wallpapers.append(Wallpaper(wallpaper_pack=self, path=os.path.join(wallpapers_path, wallpaper)))


        return wallpapers