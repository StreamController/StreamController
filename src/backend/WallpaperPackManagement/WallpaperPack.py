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
from pathlib import Path

# Import own modules
from src.backend.WallpaperPackManagement.Wallpaper import Wallpaper

class WallpaperPack:
    def __init__(self, path: str):
        self.path = path
        self.is_valid = True
        self.name = self.get_manifest().get("name") or os.path.basename(path)
        self.pack_structure: dict[str, list[Wallpaper]] = {}

        self.generate_folder_structure("images")


    @lru_cache(maxsize=None)
    def get_manifest(self):
        path = Path(os.path.join(self.path, "manifest.json"))

        if not path.exists(follow_symlinks=True):
            self.is_valid = False
            return {}

        return self.get_json(path)

    @lru_cache(maxsize=None)
    def get_attribution_json(self):
        path = Path(os.path.join(self.path, "attribution.json"))

        return self.get_json(path)

    @lru_cache(maxsize=None)
    def get_pack_attribution(self):
        attribution = self.get_attribution_json()
        return attribution.get("default", attribution.get("general", attribution.get("generic", {})))

    @lru_cache(maxsize=None)
    def get_json(self, json_path: Path):
        if not json_path.exists(follow_symlinks=True):
            return {}

        with open(json_path) as f:
            return json.load(f)

    @lru_cache(maxsize=None)
    def get_thumbnail_path(self):
        manifest = self.get_manifest()
        path = Path(os.path.join(self.path, manifest.get("thumbnail")))
        if path.exists(follow_symlinks=True):
            return path
        self.is_valid = False
        return None

    def get_wallpapers(self) -> list[Wallpaper]:
        return self.get_content_from_structure()

    def get_content_from_structure(self) -> list[Wallpaper]:
        content: list[Wallpaper] = []

        for folder_name, folder_entry in self.pack_structure.items():
            for entry in folder_entry:
                content.append(entry)

        return content

    def generate_folder_structure(self, asset_path: str):
        manifest = self.get_manifest()

        if self.is_valid is False:
            return

        asset_path = manifest.get(asset_path)
        pack_path = Path(os.path.join(self.path, asset_path))

        if not pack_path.exists(follow_symlinks=True):
            self.is_valid = False
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
            content.append(Wallpaper(wallpaper_pack=self, path=entry.path))

        return content