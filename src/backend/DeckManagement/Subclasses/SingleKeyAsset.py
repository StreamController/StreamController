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
    def __init__(self, controller_key: "ControllerKey"):
        self.controller_key = controller_key
        self.deck_controller = controller_key.deck_controller

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
        layout = self.controller_key.layout_manager.get_composed_layout()

        foreground = self.get_raw_image()
        if foreground is None:
            foreground = self.deck_controller.generate_alpha_key()

        img_size = self.deck_controller.get_key_image_size()
        scaled_img_size = (int(img_size[0] * layout.size), int(img_size[1] * layout.size))  # Calculate scaled size of the image

        if layout.fill_mode == "stretch":
            foreground_resized = foreground.resize(scaled_img_size, Image.Resampling.HAMMING)

        elif layout.fill_mode == "cover":
            foreground_resized = ImageOps.cover(foreground, scaled_img_size, Image.Resampling.HAMMING)

        elif layout.fill_mode == "contain":
            foreground_resized = ImageOps.contain(foreground, scaled_img_size, Image.Resampling.HAMMING)

        # Adjust the calculation for margins so that halign and valign of 0 will center the foreground
        halign = layout.halign if layout.size <= 1 else -layout.halign
        valign = layout.valign if layout.size <= 1 else -layout.valign

        left_margin = int((background.width - scaled_img_size[0]) * (halign + 1) / 2)
        top_margin = int((background.height - scaled_img_size[1]) * (valign + 1) / 2)

        # Create a new image for the resulting composite
        final_image = Image.new('RGBA', background.size, (0, 0, 0, 0))
        final_image.paste(background, (0, 0))  # Paste the background onto the composite image

        # Paste the resized foreground onto the final image at the calculated position
        final_image.paste(foreground_resized, (left_margin, top_margin), foreground_resized if foreground.mode == "RGBA" else None)

        return final_image
    
    def close(self):
        pass