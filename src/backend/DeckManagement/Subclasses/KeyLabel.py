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
from src.backend.DeckManagement.Subclasses.SingleKeyAsset import SingleKeyAsset
from PIL import Image, ImageFont
from dataclasses import dataclass
import matplotlib.font_manager
from functools import lru_cache
from fontTools.ttLib import TTFont
import subprocess
import os

import globals as gl

# Add symbol fonts to matplotlib at startup
_symbol_fonts_added = False
def _ensure_symbol_fonts():
    global _symbol_fonts_added
    if _symbol_fonts_added:
        return
    
    # Common symbol font names - use fc-match to find actual paths
    symbol_font_names = ["Webdings", "Wingdings"]
    
    for font_name in symbol_font_names:
        try:
            result = subprocess.run(
                ["fc-match", "-f", "%{file}", font_name],
                capture_output=True, text=True, timeout=2
            )
            if result.returncode == 0 and result.stdout.strip():
                font_path = result.stdout.strip()
                if os.path.exists(font_path):
                    try:
                        matplotlib.font_manager.fontManager.addfont(font_path)
                    except Exception:
                        pass
        except Exception:
            pass
    
    _symbol_fonts_added = True

@lru_cache(maxsize=128)
def _is_symbol_font(font_path: str) -> bool:
    """Check if font uses symbol encoding (e.g., Webdings, Wingdings).
    
    Symbol fonts have a cmap table with platformID=3 (Windows) and 
    platEncID=0 (Symbol encoding). Results are cached.
    """
    try:
        font = TTFont(font_path)
        for table in font['cmap'].tables:
            if table.platformID == 3 and table.platEncID == 0:
                return True
        return False
    except Exception:
        return False


from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from src.backend.DeckManagement.DeckController import ControllerKey

@dataclass
class KeyLabel:
    controller_input: "ControllerKey"
    text: str = None
    font_size: int = None
    font_name: str = None
    font_weight: int = None
    style: str = None # normal, oblique, italic
    color: list[int] = None
    outline_width: int = None
    outline_color: list[int] = None
    alignment: str = None  # left, center, right

    def get_font_path(self) -> str:
        font_name = self.font_name
        if self.font_name in ["", None]:
            font_name = gl.fallback_font

        # Ensure symbol fonts are available to matplotlib
        _ensure_symbol_fonts()

        return matplotlib.font_manager.findfont(
            matplotlib.font_manager.FontProperties(
                family=font_name,
                weight=self.font_weight,
                size=self.font_size,
                style=self.style
            )
        )

    def clear_values(self):
        self.text = None
        self.font_size = None
        self.font_name = None
        self.font_weight = None
        self.color = None
        self.outline_width = None
        self.outline_color = None
        self.alignment = None

    def get_font(self) -> ImageFont.FreeTypeFont:
        font_path = self.get_font_path()
        encoding = "symb" if _is_symbol_font(font_path) else "unic"
        return ImageFont.truetype(font_path, self.font_size, encoding=encoding)