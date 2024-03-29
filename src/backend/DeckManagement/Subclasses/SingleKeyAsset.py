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
    from src.backend.DeckManagement.DeckController import ControllerKey

class SingleKeyAsset:
    def __init__(self, controller_key: "ControllerKey", fill_mode: str = "cover", size: float = 1, valign: float = 0, halign: float = 0):
        self.controller_key = controller_key
        self.deck_controller = controller_key.deck_controller
        self.fill_mode = fill_mode
        self.size = size
        self.valign = valign
        self.halign = halign

    def get_raw_image(self) -> Image.Image:
        return Image.open(os.path.join("Assets", "images", "error.png"))
    
    def add_labels_to_image(self, image: Image.Image, labels: dict) -> Image.Image:
        draw = ImageDraw.Draw(image)
        draw.fontmode = "1" # Anti-aliased - this prevents frayed/noisy labels on the deck

        for label in dict(labels):
            text = labels[label].text
            if text in [None, ""]:
                continue
            # text = "text"
            font_path = labels[label].get_font_path()
            color = tuple(labels[label].color)
            font_size = labels[label].font_size
            font = ImageFont.truetype(font_path, font_size)
            font_weight = labels[label].font_weight

            if text is None:
                continue
            
            if label == "top":
                position = (image.width / 2, font_size*1.125)

            if label == "center":
                position = (image.width / 2, (image.height + font_size) / 2 - 3)

            if label == "bottom":
                position = (image.width / 2, image.height*0.875)


            draw.text(position,
                        text=text, font=font, anchor="ms",
                        fill=color, stroke_width=font_weight)
            
        draw = None
        del draw

        return image.copy()
    
    def generate_final_image(self, background: Image.Image = None, labels: dict = {}) -> Image.Image:
        foreground = self.get_raw_image()
        if foreground is None:
            foreground = self.deck_controller.generate_alpha_key()

        img_size = self.deck_controller.get_key_image_size()
        img_size = (int(img_size[0] * self.size), int(img_size[1] * self.size)) # Calculate scaled size of the image
        if self.fill_mode == "stretch":
            foreground_resized = foreground.resize(img_size, Image.Resampling.HAMMING)

        elif self.fill_mode == "cover":
            foreground_resized = ImageOps.cover(foreground, img_size, Image.Resampling.HAMMING)

        elif self.fill_mode == "contain":
            foreground_resized = ImageOps.contain(foreground, img_size, Image.Resampling.HAMMING)

        left_margin = int((background.width - img_size[0]) * (self.halign + 1) / 2)
        top_margin = int((background.height - img_size[1]) * (self.valign + 1) / 2)

        if foreground.mode == "RGBA":
            background.paste(foreground_resized, (left_margin, top_margin), foreground_resized)
        else:
            background.paste(foreground_resized, (left_margin, top_margin))
        
        return background