from typing import Tuple

from PIL import Image

from src.backend.DeckManagement.HelperMethods import is_image, is_svg
import globals as gl

class ImageLayer:
    def __init__(self, image, size: float = 1.0, halign: float = 0.0, valign: float = 0.0):
        self.image: Image = image
        self.size = size
        self.halign = halign
        self.valign = valign

    def transform(self, base_size) -> Tuple[Image, Tuple[int, int]]:
        new_width = int(base_size[0] * self.size)
        new_height = int(base_size[1] * self.size)
        scaled_image = self.image.resize((new_width, new_height), Image.Resampling.LANCZOS)

        x_offset = (base_size[0] - new_width) // 2
        y_offset = (base_size[1] - new_height) // 2

        x_offset -= int((base_size[0] - (base_size[0] - new_width)) * self.halign)
        y_offset -= int((base_size[1] - (base_size[1] - new_height)) * self.valign)

        return scaled_image, (x_offset, y_offset)

    @classmethod
    def from_media_path(cls, media_path: str, size: float = 1.0, halign: float = 0.0, valign: float = 0.0):
        if is_image(media_path):
            with Image.open(media_path) as img:
                image = img.copy()
        elif is_svg(media_path):
            image = gl.media_manager.generate_svg_thumbnail(media_path)
        else:
            return None

        return cls(
            image=image,
            size=size,
            halign=halign,
            valign=valign
        )