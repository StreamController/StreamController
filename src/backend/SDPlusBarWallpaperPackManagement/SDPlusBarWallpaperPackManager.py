"""
Author: Core447
Year: 2024

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
any later version.

This programm comes with ABSOLUTELY NO WARRANTY!

You should have received a copy of the GNU General Public License
along with this program. If not, see <https://www.gnu.org/licenses/>.
"""

# Import Python modules
from functools import lru_cache
import json
import os
import shutil
from loguru import logger as log

# Import globals
import globals as gl

# Import own modules
from src.backend.SDPlusBarWallpaperPackManagement.SDPlusBarWallpaperPack import SDPlusBarWallpaperPack

class SDPlusBarWallpaperPackManager:
    def __init__(self):
        self.packs = {}

    def get_wallpaper_packs(self) -> dir:
        packs = {}
        os.makedirs(os.path.join(gl.DATA_PATH, "sd_plus_bar_wallpapers"), exist_ok=True)
        for pack in os.listdir(os.path.join(gl.DATA_PATH, "sd_plus_bar_wallpapers")):
            wallpaper_pack = SDPlusBarWallpaperPack(os.path.join(gl.DATA_PATH, "sd_plus_bar_wallpapers", pack))
            if wallpaper_pack.is_valid:
                packs[pack] =  wallpaper_pack
            else:
                log.warning(f"SD+ Bar Wallpaper pack {pack} is not valid.")
        return packs

    def get_pack_wallpapers(self, wallpaper_pack: dict):
        path = wallpaper_pack.get("path")
        wallpaper_path = os.path.join(path, "wallpapers")

        wallpapers = {}
        if os.path.exists(wallpaper_path):
            for wallpaper in os.listdir(wallpaper_path):
                wallpapers.setdefault(wallpaper, {})
                wallpapers[wallpaper] =  self.get_wallpaper_attribution(wallpaper_pack.get("attribution"), wallpaper)

        return wallpapers
    
    @lru_cache
    def get_wallpaper_attribution(self, attribution:dict, wallpaper_name: str) -> dict:
        if wallpaper_name in attribution:
            # Use specific
            return attribution[wallpaper_name]
        else:
            # Use default
            return attribution.get("generic", attribution.get("default", attribution.get("general")))

