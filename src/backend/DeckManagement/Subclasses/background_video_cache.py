import hashlib
import os
import sys
import threading
import time
from PIL import Image, ImageOps
import cv2
from StreamDeck.ImageHelpers import PILHelper

VID_CACHE = "vid_cache"

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
        self.key_count = self.deck_controller.deck.key_count()
        self.key_size = self.deck_controller.deck.key_image_format()['size']
        self.spacing = self.deck_controller.spacing

        self.load_cache()

        if self.is_cache_complete():
            print("Cache is complete. Closing the video capture.")
            self.release()
        else:
            print("Cache is not complete. Continuing with video capture.")

        # Print size of cache in memory in mb:
        print(f"Size of cache in memory: {sys.getsizeof(self.cache) / 1024 / 1024:.2f} MB")

        print(f"Size of capture: {sys.getsizeof(self.cap) / 1024 / 1024:.2f} MB")

    def get_tiles(self, n):
        n = min(n, self.n_frames - 1)
        with self.lock:
            if self.is_cache_complete():
                print("Cache is complete. Retrieving frame from cache.")
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

                    # Write the tile to the cache
                    self.write_cache(key_image, self.last_frame_index, key)

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

    def write_cache(self, image: Image, frame_index: int, key_index: int = None):
        # Create the directory if it doesn't exist
        cache_dir = os.path.join(VID_CACHE, "3x5", self.video_md5, str(key_index))
        os.makedirs(cache_dir, exist_ok=True)
        
        # Construct the file path
        frame_file_path = os.path.join(cache_dir, f"{frame_index}.png")
        
        # Save the image as a PNG file
        image.save(frame_file_path)

    def load_cache(self, key_index: int = None):
        """
        #TODO: Too slow
        #TODO: Catch corrupt image errors
        """
        return
        # Path to the cache directory
        cache_dir = os.path.join(VID_CACHE, "3x5", self.video_md5, str(key_index) if key_index is not None else "")
        
        # Check if cache directory exists
        if os.path.exists(cache_dir) and os.path.isdir(cache_dir):
            # Iterate over each file in the directory
            for frame in os.listdir(os.path.join(cache_dir, "0")):
                tiles: list[Image.Image] = []
                s = sorted(os.listdir(cache_dir), key=lambda x: int(x))
                for key in s:
                    with Image.open(os.path.join(cache_dir, key, frame)) as img:
                        tiles.append(img.copy())

                self.cache[int(frame.split(".")[0])] = tiles


    def is_cache_complete(self) -> bool:
        return False
           # Path to the video's cache directory
        video_cache_dir = os.path.join(VID_CACHE, "3x5", self.video_md5)
        
        # Check if the video's cache directory exists
        if not os.path.exists(video_cache_dir):
            return False
        
        # Check each key's folder
        for key_index in range(15):  # Assuming 15 keys as per the provided code
            key_cache_dir = os.path.join(video_cache_dir, str(key_index))
            
            # Check if the key's folder exists and is a directory
            if not os.path.exists(key_cache_dir) or not os.path.isdir(key_cache_dir):
                return False
            
            # Get the list of files in the key's folder
            frame_files = [f for f in os.listdir(key_cache_dir) if f.endswith('.png')]
            
            # Check if the number of frame images is equal to the expected number of frames
            if len(frame_files) != self.n_frames:
                print(f"Key {key_index} has {len(frame_files)} frame images, expected {self.n_frames}")
                return False
        
        # If all checks passed, the cache is complete
        return True

if __name__ == "__main__":
    vid = BackgroundVideoCache("Kugelbahn.mp4")

    s = time.time()

    print("getting")
    frame = vid.get_tiles(1000)
    print(frame)

    e = time.time()
    print(e - s)

# frame.show()
