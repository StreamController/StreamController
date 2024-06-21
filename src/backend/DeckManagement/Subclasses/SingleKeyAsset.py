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

from PIL import Image, ImageOps, ImageDraw, ImageFont
import os

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from src.backend.DeckManagement.DeckController import ControllerInput

class SingleKeyAsset:
    def __init__(self, controller_input: "ControllerInput"):
        self.controller_input = controller_input
        self.deck_controller = controller_input.deck_controller

    def get_raw_image(self) -> Image.Image:
        return Image.open(os.path.join("Assets", "images", "error.png"))
    
    def close(self):
        pass