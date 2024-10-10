from typing import Tuple
from PIL import Image
from src.backend.DeckManagement.HelperMethods import is_image, is_svg
import globals as gl
from loguru import logger as log

class ImageLayer:
    def __init__(self, image: Image.Image, size: float = 1.0, halign: float = 0.0, valign: float = 0.0):
        """
        Initializes an ImageLayer instance.

        Args:
            image (PIL.Image.Image): The image to be layered.
            size (float, optional): Size of the image as a percentage of the base size. Defaults to 1.0.
            halign (float, optional): Horizontal alignment offset. Negative moves left, positive moves right. Defaults to 0.0.
            valign (float, optional): Vertical alignment offset. Negative moves up, positive moves down. Defaults to 0.0.
        """
        self.image: Image.Image = image
        self.size = size
        self.halign = halign
        self.valign = valign

    @classmethod
    def from_image_path(cls, media_path: str, size: float = 1.0, halign: float = 0.0, valign: float = 0.0) -> "ImageLayer":
        """
        Creates an ImageLayer from a media path.

        Args:
            media_path (str): The full path to the image.
            size (float, optional): Size of the image as a percentage. Defaults to 1.0.
            halign (float, optional): Horizontal offset for image alignment. Negative for left, positive for right. Defaults to 0.0.
            valign (float, optional): Vertical offset for image alignment. Negative for top, positive for bottom. Defaults to 0.0.

        Returns:
            ImageLayer: An instance of the ImageLayer class with the loaded image.
        """
        if is_image(media_path):
            with Image.open(media_path) as img:
                image = img.copy()
        elif is_svg(media_path):
            image = gl.media_manager.generate_svg_thumbnail(media_path)
        else:
            log.error(f"{media_path} is not an Image!")
            return None

        return cls(
            image=image,
            size=size,
            halign=halign,
            valign=valign
        )

    def transform(self, base_size: Tuple[int, int]) -> Tuple[Image.Image, Tuple[int, int]]:
        """
        Transforms the current image relative to the base image size it will be pasted on.

        Args:
            base_size (tuple[int, int]): The size of the base image (width, height).

        Returns:
            tuple[PIL.Image.Image, tuple[int, int]]: A tuple containing the resized image and its position (x, y).
        """
        new_width = int(base_size[0] * self.size)
        new_height = int(base_size[1] * self.size)
        scaled_image = self.image.resize((new_width, new_height), Image.Resampling.LANCZOS)

        x_offset = (base_size[0] - new_width) // 2
        y_offset = (base_size[1] - new_height) // 2

        x_offset += int((base_size[0] - (base_size[0] - new_width)) * self.halign)
        y_offset -= int((base_size[1] - (base_size[1] - new_height)) * self.valign)

        return scaled_image, (x_offset, y_offset)
