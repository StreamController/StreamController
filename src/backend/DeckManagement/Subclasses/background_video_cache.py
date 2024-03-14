import bz2
import hashlib
import os
import pickle
import sys
import threading
import time
from PIL import Image, ImageOps
import cv2
from StreamDeck.ImageHelpers import PILHelper
import indexed_bzip2 as ibz2
from loguru import logger as log

import globals as gl

VID_CACHE = os.path.join(gl.DATA_PATH, "cache", "videos")
os.makedirs(VID_CACHE, exist_ok=True)

# Import typing
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from src.backend.DeckManagement.DeckController import DeckController

class BackgroundVideoCache:
    def __init__(self, video_path, deck_controller: "DeckController") -> None:
        self.deck_controller = deck_controller
        self.lock = threading.Lock()

        self.video_path = video_path
        self.cap = cv2.VideoCapture(video_path)
        self.n_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.cache = {}
        self.last_decoded_frame = None
        self.last_frame_index = -1

        self.video_md5 = self.get_video_hash()

        self.key_layout = self.deck_controller.deck.key_layout()
        self.key_layout_str = f"{self.key_layout[0]}x{self.key_layout[1]}"
        self.key_count = self.deck_controller.deck.key_count()
        self.key_size = self.deck_controller.deck.key_image_format()['size']
        self.spacing = self.deck_controller.spacing

        self.cache_stored = False

        thread = threading.Thread(target=self.load_cache)
        thread.start()

        if self.is_cache_complete():
            log.info("Cache is complete. Closing the video capture.")
            self.release()
        else:
            log.info("Cache is not complete. Continuing with video capture.")

    def get_tiles(self, n):
        n = min(n, self.n_frames - 1)
        with self.lock:
            if self.is_cache_complete():
                return self.cache.get(n, None)

            # Otherwise, continue with video capture
            # Check if the frame is already decoded
            if n in self.cache:
                return self.cache[n]

            # If the requested frame is before the last decoded one, reset the capture
            if n < self.last_frame_index:
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, n)
                self.last_frame_index = n - 1

            # Decode frames until the nth frame
            while self.last_frame_index < n:
                success, frame = self.cap.read()
                if not success:
                    break  # Reached the end of the video
                self.last_frame_index += 1
                
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)  
                pil_image = Image.fromarray(frame_rgb)

                # Resize the image
                full_sized = self.create_full_deck_sized_image(pil_image)

                tiles: list[Image.Image] = []
                for key in range(self.key_count):
                    key_image = self.crop_key_image_from_deck_sized_image(full_sized, key)
                    tiles.append(key_image)

                    if n >= self.n_frames - 1:
                        self.save_cache_threaded()

                self.cache[self.last_frame_index] = tiles

                full_sized.close()
                pil_image.close()


        # Return the last decoded frame if the nth frame is not available
        return self.cache.get(n, tiles)
    
    def create_full_deck_sized_image(self, frame: Image.Image) -> Image.Image:
        key_width *= self.key_layout[0]
        key_height *= self.key_layout[1]

        # Compute the total number of extra non-visible pixels that are obscured by
        # the bezel of the StreamDeck.
        spacing_x *= self.key_layout[0] - 1
        spacing_y *= self.key_layout[1] - 1

        # Compute final full deck image size, based on the number of buttons and
        # obscured pixels.
        full_deck_image_size = (key_width + spacing_x, key_height + spacing_y)

        # Resize the image to suit the StreamDeck's full image size. We use the
        # helper function in Pillow's ImageOps module so that the image's aspect
        # ratio is preserved.
        return ImageOps.fit(frame, full_deck_image_size, Image.Resampling.HAMMING)
    
    def crop_key_image_from_deck_sized_image(self, image: Image.Image, key):
        # deck = self.deck_controller.deck
        key_rows, key_cols = self.key_layout
        key_width, key_height = self.key_size
        spacing_x, spacing_y = self.spacing

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

        return segment

    def release(self):
        with self.lock:
            self.cap.release()

    def get_video_hash(self) -> str:
        sha1sum = hashlib.md5()
        with open(self.video_path, 'rb') as video:
            block = video.read(2**16)
            while len(block) != 0:
                sha1sum.update(block)
                block = video.read(2**16)
            return sha1sum.hexdigest()
        
    def save_cache_threaded(self):
        t = threading.Thread(target=self.save_cache)
        t.start()
        
    def save_cache(self):
        """
        Store cache using pickle
        """
        if self.cache_stored:
            return
        self.cache_stored = True
        
        start = time.time()
        cache_path = os.path.join(VID_CACHE, self.key_layout_str, f"{self.video_md5}.cache")
        os.makedirs(os.path.dirname(cache_path), exist_ok=True)

        data = self.cache.copy()

        with bz2.open(cache_path, "wb") as f:
            pickle.dump(data, f)

        log.success(f"Saved cache in {time.time() - start:.2f} seconds")
        self.last_save = time.time()


    def load_cache(self, key_index: int = None):
        cache_path = os.path.join(VID_CACHE, self.key_layout_str, f"{self.video_md5}.cache")
        if not os.path.exists(cache_path):
            return
        
        # with open(os.path.join(VID_CACHE, "3x5", f"{self.video_md5}.pkl"), "rb") as f:
            # self.cache = pickle.load(f)
        
        # return
        _time = time.time()
        try:
            with ibz2.open(cache_path, parallelization=os.cpu_count()) as f:
                self.cache = pickle.load(f)
            log.success(f"Loaded cache in {time.time() - _time:.2f} seconds")
        except Exception as e:
            os.remove(cache_path)
            log.error(f"Failed to load cache: {e}")
            return

    def is_cache_complete(self) -> bool:
        if self.n_frames != len(self.cache):
            return False
        
        for key in self.cache:
            if len(self.cache[key]) != self.key_count:
                return False

        return True