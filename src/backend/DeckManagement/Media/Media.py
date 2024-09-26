from typing import List, Union

from .ImageLayer import ImageLayer
from PIL import Image
from loguru import logger as log

class Media:
    def __init__(self, size: float = 1.0, halign: float = 0.0, valign: float = 0.0, layers: List[ImageLayer] = None):
        self.layers: List[ImageLayer] = layers or []
        self.size = size
        self.halign = halign
        self.valign = valign

    @classmethod
    def from_media_path(cls, media_path: str, size: float = 1.0, halign: float = 0.0, valign: float = 0.0):
        """
        Creates a new media, adding the media path directly as a new layer
        @return: A new Media Object with the added Image
        """
        layer = ImageLayer.from_media_path(media_path)
        return cls(size=size, halign=halign, valign=valign, layers=[layer])

    def add_layer(self, layers: Union[ImageLayer, List[ImageLayer]]):
        for layer in layers:
            if isinstance(layer, list):
                self.layers.extend(layer)
            if isinstance(layer, ImageLayer):
                self.layers.append(layer)

    def add_layer_below(self, *args: Union[ImageLayer, List[ImageLayer]]):
        """Adds the layers below the current existing ones"""
        for arg in args:
            if isinstance(arg, list):
                self.layers.extend(arg)
            if isinstance(arg, ImageLayer):
                self.layers.append(arg)

    def add_layer_on_top(self, *args: Union[ImageLayer, List[ImageLayer]]):
        """Adds the layers ontop of the current existing ones"""
        result = []

        for arg in args:
            if isinstance(arg, list):
                result.extend(arg)
            if isinstance(arg, ImageLayer):
                result.append(arg)

        result.extend(self.layers)
        self.layers = result

    def get_final_media(self) -> Image:
        """
        Transforms the layers list into a final image. The result of this image should be used sparingly because it takes some processing power and could be slow
        @return: Gives the final image that can be displayed by using set_media
        """
        if not self.layers and len(self.layers) <= 0:
            return

        pre_image = Image.new('RGBA', self.layers[0].image.size)

        for layer in self.layers:
            if not layer:
                log.error("Layer not defined")
                continue
            image, position = layer.transform(pre_image.size)
            pre_image.paste(image, position, image)

        post_image_layer = ImageLayer(image=pre_image, size=self.size, halign=self.halign, valign=self.valign)

        base_image = Image.new('RGBA', post_image_layer.image.size)

        image, position = post_image_layer.transform(base_image.size)

        base_image.paste(image, position, image)

        return base_image