"""
Author: gensyn
Year: 2025

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
any later version.

This programm comes with ABSOLUTELY NO WARRANTY!

You should have received a copy of the GNU General Public License
along with this program. If not, see <https://www.gnu.org/licenses/>.
"""
# Import own modules
from src.windows.AssetManager.Preview import Preview


class AssetPreview(Preview):
    def __init__(self, asset: dict):
        super().__init__(
            image_path=asset["icon_path"],
            text=asset["name"],
            can_be_deleted=False,
            has_info=False
        )
        self.set_hexpand(False)
        self.asset = asset
