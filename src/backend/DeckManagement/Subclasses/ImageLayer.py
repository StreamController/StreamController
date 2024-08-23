from typing import Tuple, Union, List

from PIL import Image

from src.backend.DeckManagement.HelperMethods import is_image, is_svg
import globals as gl
from loguru import logger as log

class ImageLayer:
    def __init__(self, image: Image, size: float = 1.0, halign: float = 0.0, valign: float = 0.0):
        self.image: Image = image
        """Direct Gtk.Image"""
        self.size = size
        """Size in %"""
        self.halign = halign
        """Offset on the Horizontal axis (<0 Left | >0 Right)"""
        self.valign = valign
        """Offset on the Vertical axis (<0 Top | >0 Bottom)"""

    @classmethod
    def from_media_path(cls, media_path: str, size: float = 1.0, halign: float = 0.0,
                        valign: float = 0.0) -> "ImageLayer":
        """
        Creates an ImageLayer from a media path
        @param media_path: The full path to the Image
        @param size: Size of the image in %
        @param halign: Horizontal offset in which to move the Image. (<0 Left | >0 Right)
        @param valign: Vertical offset in which to move the Image. (<0 Top | >0 Bottom)
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

    def transform(self, base_size: Tuple[int, int]) -> Tuple[Image, Tuple[int, int]]:
        """
        Transforms the current image in relation to the Image it will be pasted on
        @param base_size: Size of the image it will be pasted on
        @return: Returns the scaled image and the position on the X and Y Axis
        """

        new_width = int(base_size[0] * self.size)
        new_height = int(base_size[1] * self.size)
        scaled_image = self.image.resize((new_width, new_height), Image.Resampling.LANCZOS)

        x_offset = (base_size[0] - new_width) // 2
        y_offset = (base_size[1] - new_height) // 2

        x_offset += int((base_size[0] - (base_size[0] - new_width)) * self.halign)
        y_offset -= int((base_size[1] - (base_size[1] - new_height)) * self.valign)

        return scaled_image, (x_offset, y_offset)

    def layer_on_top(self, *args: Union["ImageLayer", List["ImageLayer"]]) -> Image:
        """
        Creates a complete Gtk.Image but pastes the other Layers on top of it. The current Image will be at the very bottom
        @param args: Layers that will be pasted on top of the current one
        @return: A finished Image with all Layers pasted onto each other
        """

        layers = ImageLayer.to_layer_list(self, *args)
        return ImageLayer.to_layered_image(layers)

    def layer_below(self, *args: Union["ImageLayer", List["ImageLayer"]]) -> Image:
        """
        Creates a complete Gtk.Image but pastes the other Layers on top of it. The current Image will be at the very top
        @param args: Layers that will be pasted below of the current one
        @return: A finished Image with all Layers pasted onto each other
        """

        layers = ImageLayer.to_layer_list(*args, self)
        return ImageLayer.to_layered_image(layers)

    @staticmethod
    def to_layer_list(*args: Union["ImageLayer", List["ImageLayer"]]) -> List["ImageLayer"]:
        """Unifies different Layers into one List of ImageLayers"""
        result = []

        for arg in args:
            if isinstance(arg, list):
                result.extend(arg)
            else:
                result.append(arg)

        return result

    @staticmethod
    def to_layered_image(layers: List["ImageLayer"]) -> Image:
        """
        Will Create a complete Gtk.Image from the Layers where [0] will be on the very bottom and [-1] on the very Top
        @return: A finished Image with all Layers pasted onto each other
        """

        base_image = Image.new('RGBA', layers[0].image.size)

        for layer in layers:
            if not layer:
                log.error("A layer is not defined!")
                continue
            image, position = layer.transform(base_image.size)
            base_image.paste(image, position, image)

        return base_image