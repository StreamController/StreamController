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

# Import typing
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from src.backend.SDPlusBarWallpaperPackManagement.SDPlusBarWallpaperPack import SDPlusBarWallpaperPack

class SDPlusBarWallpaper:
    def __init__(self, wallpaper_pack: "SDPlusBarWallpaperPack", path: str):
        self.wallpaper_pack = wallpaper_pack
        self.path = path

        self.name = os.path.splitext(os.path.basename(path))[0]

    def get_attribution(self):
        attribution = self.wallpaper_pack.get_attribution_json()
        pack_path = self.wallpaper_pack.path

        rel_path = os.path.relpath(self.path, pack_path)

        if rel_path in attribution:
            return attribution[rel_path]
        else:
            return attribution.get("default", attribution.get("general", attribution.get("generic", {})))

