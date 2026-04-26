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
import gc
import os
from typing import TYPE_CHECKING

from PIL import Image, ImageOps
from StreamDeck.ImageHelpers import PILHelper

from src.backend.DeckManagement.HelperMethods import is_video
from src.backend.DeckManagement.Subclasses.background_video_cache import BackgroundVideoCache
from src.backend.PageManagement.Page import Page

if TYPE_CHECKING:
    from src.backend.DeckManagement.DeckController import DeckController


class Background:
    def __init__(self, deck_controller: "DeckController"):
        self.deck_controller = deck_controller

        self.image = None
        self.video = None

        self.tiles: list[Image.Image] = [None] * deck_controller.deck.key_count()

    def set_image(self, image: "BackgroundImage", update: bool = True) -> None:
        self.image = image
        if self.video is not None:
            self.video.close()
        self.video = None
        gc.collect()

        self.update_tiles()
        if update:
            self.deck_controller.update_all_inputs()

    def set_video(self, video: "BackgroundVideo", update: bool = True) -> None:
        if self.video is not None:
            self.video.close()
        self.image = None
        self.video = video
        gc.collect()

        self.update_tiles()
        if update:
            self.deck_controller.update_all_inputs()

    def set_from_path(self, path: str, fps: int = 30, loop: bool = True, update: bool = True, allow_keep: bool = True) -> None:
        if path == "":
            path = None
        if path is None:
            self.image = None
            # self.video = None
            self.set_video(None, update=False)
            self.update_tiles()
            if update:
                self.deck_controller.update_all_inputs()
        elif is_video(path):
            if allow_keep:
                if self.video is not None and self.video.video_path == path:
                    self.video.page = self.deck_controller.active_page
                    self.video.fps = fps
                    self.video.loop = loop
                    return
            self.set_video(BackgroundVideo(self.deck_controller, path, loop=loop, fps=fps), update=update)
        else:
            if path is None:
                return
            if not os.path.isfile(path):
                return
            with Image.open(path) as image:
                self.set_image(BackgroundImage(self.deck_controller, image.copy()), update=update)

    def update_tiles(self) -> None:
        old_tiles = self.tiles # Why store them and close them later? So that there is not key error if the media threads fetches them during the update
        if self.image is not None:
            self.tiles = self.image.get_tiles()
        elif self.video is not None:
            self.tiles = self.video.get_next_tiles()
        else:
            self.tiles = [self.deck_controller.generate_alpha_key() for _ in range(self.deck_controller.deck.key_count())]

        for tile in old_tiles:
            if tile is not None:
                tile.close()
                tile = None
                del tile
        del old_tiles

class BackgroundImage:
    def __init__(self, deck_controller: "DeckController", image: Image) -> None:
        self.deck_controller = deck_controller
        self.image = image

    def create_full_deck_sized_image(self) -> Image:
        key_rows, key_cols = self.deck_controller.deck.key_layout()
        key_width, key_height = self.deck_controller.get_key_image_size()
        spacing_x, spacing_y = self.deck_controller.key_spacing

        key_width *= key_cols
        key_height *= key_rows

        # Compute the total number of extra non-visible pixels that are obscured by
        # the bezel of the StreamDeck.
        spacing_x *= key_cols - 1
        spacing_y *= key_rows - 1

        # Compute final full deck image size, based on the number of buttons and
        # obscured pixels.
        full_deck_image_size = (key_width + spacing_x, key_height + spacing_y)

        # Convert to RGBA first to preserve transparency, then resize
        img_rgba = self.image.convert("RGBA")
        return ImageOps.fit(img_rgba, full_deck_image_size, Image.LANCZOS)
    
    def crop_key_image_from_deck_sized_image(self, image: Image.Image, key):
        deck = self.deck_controller.deck


        key_rows, key_cols = deck.key_layout()
        key_width, key_height = deck.key_image_format()['size']
        spacing_x, spacing_y = self.deck_controller.key_spacing

        # Determine which row and column the requested key is located on.
        row = key // key_cols
        col = key % key_cols

        # Compute the starting X and Y offsets into the full size image that the
        # requested key should display.
        start_x = col * (key_width + spacing_x)
        start_y = row * (key_height + spacing_y)

        # Compute the region of the larger deck image that is occupied by the given
        # key, and crop out that segment of the full image.
        region = (start_x, start_y, start_x + key_width, start_y + key_height)
        segment = image.crop(region)

        # Return the segment directly, converting to RGBA to preserve transparency
        return segment.convert("RGBA")
    
    def get_tiles(self) -> list[Image.Image]:
        full_deck_sized_image = self.create_full_deck_sized_image()

        tiles: list[Image.Image] = []
        for key in range(self.deck_controller.deck.key_count()):
            key_image = self.crop_key_image_from_deck_sized_image(full_deck_sized_image, key)
            tiles.append(key_image)

        return tiles

class BackgroundVideo(BackgroundVideoCache):
    def __init__(self, deck_controller: "DeckController", video_path: str, loop: bool = True, fps: int = 30) -> None:
        self.deck_controller = deck_controller
        self.video_path = video_path
        self.loop = loop
        self.fps = fps

        self.page: Page = self.deck_controller.active_page

        self.active_frame: int = -1

        super().__init__(video_path, deck_controller=deck_controller)

    def get_next_tiles(self) -> list[Image.Image]:
        # return [self.deck_controller.generate_alpha_key() for _ in range(self.deck_controller.deck.key_count())]
        self.active_frame += 1

        if self.active_frame >= self.n_frames:
            if self.loop:
                self.active_frame = 0

        tiles =  self.get_tiles(self.active_frame)
        try:
            copied_tiles = [tile.copy() for tile in tiles]
        except Exception:
            copied_tiles = [None for _ in range(len(tiles))]
        return copied_tiles

        frame = self.get_next_frame()
        frame_full_sized_image = self.create_full_deck_sized_image(frame)

        tiles: list[Image.Image] = []
        for key in range(self.deck_controller.deck.key_count()):
            key_image = self.crop_key_image_from_deck_sized_image(frame_full_sized_image, key)
            tiles.append(key_image)

        return tiles

    def get_next_frame(self) -> Image.Image:
        self.active_frame += 1

        if self.active_frame >= self.n_frames:
            if self.loop:
                self.active_frame = 0
        
        return self.get_frame(self.active_frame)
    
    def create_full_deck_sized_image(self, frame: Image.Image) -> Image.Image:
        key_rows, key_cols = self.deck_controller.deck.key_layout()
        key_width, key_height = self.deck_controller.get_key_image_size()
        spacing_x, spacing_y = self.deck_controller.key_spacing

        key_width *= key_cols
        key_height *= key_rows

        # Compute the total number of extra non-visible pixels that are obscured by
        # the bezel of the StreamDeck.
        spacing_x *= key_cols - 1
        spacing_y *= key_rows - 1

        # Compute final full deck image size, based on the number of buttons and
        # obscured pixels.
        full_deck_image_size = (key_width + spacing_x, key_height + spacing_y)

        # Resize the image to suit the StreamDeck's full image size. We use the
        # helper function in Pillow's ImageOps module so that the image's aspect
        # ratio is preserved.
        return ImageOps.fit(frame, full_deck_image_size, Image.Resampling.HAMMING)
    
    def crop_key_image_from_deck_sized_image(self, image: Image.Image, key):
        key_spacing = self.deck_controller.key_spacing
        deck = self.deck_controller.deck


        key_rows, key_cols = deck.key_layout()
        key_width, key_height = deck.key_image_format()['size']
        spacing_x, spacing_y = key_spacing

        # Determine which row and column the requested key is located on.
        row = key // key_cols
        col = key % key_cols

        # Compute the starting X and Y offsets into the full size image that the
        # requested key should display.
        start_x = col * (key_width + spacing_x)
        start_y = row * (key_height + spacing_y)

        # Compute the region of the larger deck image that is occupied by the given
        # key, and crop out that segment of the full image.
        region = (start_x, start_y, start_x + key_width, start_y + key_height)
        segment = image.crop(region)

        # Create a new key-sized image, and paste in the cropped section of the
        # larger image.
        key_image = PILHelper.create_key_image(deck)
        key_image.paste(segment)

        return key_image
