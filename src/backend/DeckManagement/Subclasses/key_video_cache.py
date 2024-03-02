from functools import lru_cache
import hashlib
import os
import sys
import threading
import time
from PIL import Image, ImageOps
import cv2
from loguru import logger as log

VID_CACHE = "vid_cache"

class VideoFrameCache:
    def __init__(self, video_path):
        self.lock = threading.Lock()

        self.video_path = video_path
        self.cap = cv2.VideoCapture(video_path)
        self.n_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.cache = {}
        self.last_decoded_frame = None
        self.last_frame_index = -1

        self.video_md5 = self.get_video_hash()

        self.frame_width: int = 72

        self.load_cache()


        if self.is_cache_complete():
            print("Cache is complete. Closing the video capture.")
            self.release()
        else:
            print("Cache is not complete. Continuing with video capture.")



        # Print size of cache in memory in mb:
        print(f"Size of cache in memory: {sys.getsizeof(self.cache) / 1024 / 1024:.2f} MB")

        print(f"Size of capture: {sys.getsizeof(self.cap) / 1024 / 1024:.2f} MB")

    def get_frame(self, n):
        if self.is_cache_complete():
            # print("Cache is complete. Retrieving frame from cache.")
            return self.cache.get(n, None)

        # Otherwise, continue with video capture
        # Check if the frame is already decoded
        if n in self.cache:
            return self.cache[n]

        # If the requested frame is before the last decoded one, reset the capture
        if n < self.last_frame_index:
            with self.lock:
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, n)
            self.last_frame_index = n - 1

        # Decode frames until the nth frame
        while self.last_frame_index < n:
            with self.lock:
                success, frame = self.cap.read()
            if not success:
                break  # Reached the end of the video
            self.last_frame_index += 1
            
            # Calculate the new height to maintain aspect ratio
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            pil_image = Image.fromarray(frame_rgb)

            # Fill a 72x72 square completely with the image, keeping the aspect ratio
            pil_image = ImageOps.fit(pil_image, (self.frame_width, self.frame_width), Image.Resampling.LANCZOS)

            self.last_decoded_frame = pil_image
            self.cache[self.last_frame_index] = pil_image

            # Write the frame to the cache
            self.write_cache(pil_image, self.last_frame_index)

        # Return the last decoded frame if the nth frame is not available
        return self.cache.get(n, self.last_decoded_frame)

    def release(self):
        with self.lock:
            self.cap.release()

    def get_video_hash(self) -> str:
        with self.lock:
            sha1sum = hashlib.md5()
            with open(self.video_path, 'rb') as video:
                block = video.read(2**16)
                while len(block) != 0:
                    sha1sum.update(block)
                    block = video.read(2**16)
                return sha1sum.hexdigest()

    def write_cache(self, image: Image, frame_index: int, key_index: int = None):
        """
        key_index: if None: single key video, if int: key index
        """
        with self.lock:
            if key_index is None:
                path = os.path.join(VID_CACHE, "single_key", self.video_md5, f"{frame_index}.jpg")
            else:
                path = os.path.join(VID_CACHE, f"key: {key_index}", self.video_md5, f"{key_index}", f"{frame_index}.jpg")

            if os.path.isfile(path):
                return
            
            os.makedirs(os.path.dirname(path), exist_ok=True)
            
            image.save(path)

    def load_cache(self, key_index: int = None):
        with self.lock:
            start = time.time()
            if key_index is None:
                path = os.path.join(VID_CACHE, "single_key", self.video_md5)
                if not os.path.exists(path):
                    return
                for file in os.listdir(path):
                    if os.path.splitext(file)[1] != ".jpg":
                        continue
                    with Image.open(os.path.join(path, file)) as img:
                        self.cache[int(file.split(".")[0])] = img.copy()

            else:
                path = os.path.join(VID_CACHE, f"key: {key_index}", self.video_md5)
                if not os.path.exists(path):
                    return
                for file in os.listdir(path):
                    if os.path.splitext(file)[1] != ".jpg":
                        continue
                    with Image.open(os.path.join(path, file)) as img:
                        self.cache[int(file.split(".")[0])] = img.copy()

            log.info(f"Loaded cache in {time.time() - start:.2f} seconds")

    @lru_cache(maxsize=None)
    def is_cache_complete(self) -> bool:
        return len(self.cache) == self.n_frames
