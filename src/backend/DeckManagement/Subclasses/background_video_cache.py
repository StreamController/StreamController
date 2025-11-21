import bz2
import hashlib
import os
import pickle
import sys
import threading
import time
from collections import OrderedDict
from typing import Dict, List, Optional, Tuple
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

class LRUCache:
    """LRU Cache implementation for video frames with memory-aware limits."""
    
    def __init__(self, max_frames: int = 100, max_memory_mb: int = 50):
        self.max_frames = max_frames
        self.max_memory_bytes = max_memory_mb * 1024 * 1024
        self.cache: OrderedDict[int, List[Image.Image]] = OrderedDict()
        self.current_memory = 0
        self.lock = threading.Lock()
        
    def _estimate_frame_memory(self, tiles: List[Image.Image]) -> int:
        """Estimate memory usage of a frame's tiles in bytes."""
        if not tiles:
            return 0
        # Rough estimate: width * height * channels * bytes_per_pixel * num_tiles
        sample_tile = tiles[0]
        channels = len(sample_tile.getbands()) if hasattr(sample_tile, 'getbands') else 3
        return sample_tile.width * sample_tile.height * channels * len(tiles)
    
    def get(self, frame_index: int) -> Optional[List[Image.Image]]:
        """Get frame from cache, updating LRU order."""
        with self.lock:
            if frame_index in self.cache:
                # Move to end (most recently used)
                tiles = self.cache.pop(frame_index)
                self.cache[frame_index] = tiles
                return tiles
            return None
    
    def put(self, frame_index: int, tiles: List[Image.Image]) -> None:
        """Put frame into cache, evicting if necessary."""
        with self.lock:
            frame_memory = self._estimate_frame_memory(tiles)
            
            # Remove existing entry if it exists
            if frame_index in self.cache:
                old_tiles = self.cache.pop(frame_index)
                self.current_memory -= self._estimate_frame_memory(old_tiles)
                # Close old images to free memory
                for tile in old_tiles:
                    tile.close()
            
            # Evict least recently used frames if needed
            while (len(self.cache) >= self.max_frames or 
                   self.current_memory + frame_memory > self.max_memory_bytes):
                if not self.cache:
                    break
                    
                oldest_frame, oldest_tiles = self.cache.popitem(last=False)
                evicted_memory = self._estimate_frame_memory(oldest_tiles)
                self.current_memory -= evicted_memory
                
                # Close evicted images to free memory
                for tile in oldest_tiles:
                    tile.close()
                    
                log.debug(f"Evicted frame {oldest_frame} ({evicted_memory/1024:.1f}KB)")
            
            # Add new frame
            self.cache[frame_index] = tiles
            self.current_memory += frame_memory
            
            log.debug(f"Cached frame {frame_index} ({frame_memory/1024:.1f}KB). "
                     f"Cache: {len(self.cache)} frames, {self.current_memory/1024/1024:.1f}MB")
    
    def clear(self) -> None:
        """Clear all cached frames."""
        with self.lock:
            for tiles in self.cache.values():
                for tile in tiles:
                    tile.close()
            self.cache.clear()
            self.current_memory = 0
    
    def __contains__(self, frame_index: int) -> bool:
        with self.lock:
            return frame_index in self.cache
    
    def get_stats(self) -> Dict[str, any]:
        """Get cache statistics."""
        with self.lock:
            return {
                "frame_count": len(self.cache),
                "memory_mb": self.current_memory / 1024 / 1024,
                "max_frames": self.max_frames,
                "max_memory_mb": self.max_memory_bytes / 1024 / 1024
            }


class BackgroundVideoCache:
    def __init__(self, video_path, deck_controller: "DeckController") -> None:
        self.deck_controller = deck_controller
        self.lock = threading.Lock()

        self.video_path = video_path
        self.cap = cv2.VideoCapture(video_path)
        self.n_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        # Replace simple dict with LRU cache
        # Get cache limits from settings or use defaults
        cache_settings = gl.settings_manager.get_app_settings().get("performance", {}).get("video-cache", {})
        max_frames = cache_settings.get("max-frames", 100)
        max_memory_mb = cache_settings.get("max-memory-mb", 50)
        
        self.cache = LRUCache(max_frames=max_frames, max_memory_mb=max_memory_mb)
        self.persistent_cache: Dict[int, List[Image.Image]] = {}  # For disk-backed complete cache
        
        self.last_decoded_frame = None
        self.last_frame_index = -1

        self.video_md5 = self.get_video_hash()

        self.key_layout = self.deck_controller.deck.key_layout()
        self.key_layout_str = f"{self.key_layout[0]}x{self.key_layout[1]}"
        self.key_count = self.deck_controller.deck.key_count()
        self.key_size = self.deck_controller.deck.key_image_format()['size']
        self.spacing = self.deck_controller.key_spacing

        self.cache_stored = False

        gl.thread_pool.submit_video_task(self.load_cache)

        if self.is_cache_complete():
            log.info("Cache is complete. Closing the video capture.")
            self.release_capture()
        else:
            log.info("Cache is not complete. Continuing with video capture.")

        self.last_tiles: List[Image.Image] = []

        self.do_caching = gl.settings_manager.get_app_settings().get("performance", {}).get("cache-videos", True)

    def get_tiles(self, n: int) -> List[Image.Image]:
        n = min(n, self.n_frames - 1)
        
        with self.lock:
            # First check LRU cache
            tiles = self.cache.get(n)
            if tiles is not None:
                return tiles
            
            # Then check persistent cache (if loaded from disk)
            if n in self.persistent_cache:
                tiles = self.persistent_cache[n]
                # Also add to LRU cache for future access
                if self.do_caching:
                    self.cache.put(n, [tile.copy() for tile in tiles])
                return tiles
            
            # If cache is complete but frame not found, return last tiles or alpha
            if self.is_cache_complete():
                if hasattr(self.cap, 'release'):
                    self.cap.release()
                return self.last_tiles if self.last_tiles else self._generate_alpha_tiles()
            
            # Otherwise, decode the frame
            tiles = self._decode_frame(n)
            
        return tiles if tiles else self._generate_alpha_tiles()
    
    def _decode_frame(self, n: int) -> Optional[List[Image.Image]]:
        """Decode a specific frame from the video."""
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

            tiles: List[Image.Image] = []
            for key in range(self.key_count):
                current_tile = self.crop_key_image_from_deck_sized_image(full_sized, key)
                tiles.append(current_tile)

            # Check if this is the last frame
            if n >= self.n_frames - 1:
                if not self.is_cache_complete():
                    self.save_cache_threaded()

            # Cache the frame
            if self.do_caching:
                self.cache.put(self.last_frame_index, [tile.copy() for tile in tiles])
            
            self.last_tiles = tiles

            full_sized.close()
            pil_image.close()

        return self.last_tiles if self.last_tiles else None
    
    def _generate_alpha_tiles(self) -> List[Image.Image]:
        """Generate alpha (transparent) tiles for missing frames."""
        return [self.deck_controller.generate_alpha_key() for _ in range(self.deck_controller.deck.key_count())]
    
    def create_full_deck_sized_image(self, frame: Image.Image) -> Image.Image:
        key_width, key_height = self.key_size
        spacing_x, spacing_y = self.spacing
        
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
    
    def crop_key_image_from_deck_sized_image(self, image: Image.Image, key: int) -> Image.Image:
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

        return segment

    def get_video_hash(self) -> str:
        sha1sum = hashlib.md5()
        with open(self.video_path, 'rb') as video:
            block = video.read(2**16)
            while len(block) != 0:
                sha1sum.update(block)
                block = video.read(2**16)
            return sha1sum.hexdigest()
        
    def save_cache_threaded(self):
        gl.thread_pool.submit_video_task(self.save_cache)
        
    @log.catch
    def save_cache(self):
        """Store cache using pickle - saves the persistent cache, not LRU cache."""
        if self.cache_stored:
            return
        self.cache_stored = True
        
        start = time.time()
        cache_path = os.path.join(VID_CACHE, self.key_layout_str, f"{self.video_md5}.cache")
        os.makedirs(os.path.dirname(cache_path), exist_ok=True)

        # Use persistent cache for saving, not the LRU cache
        data = self.persistent_cache.copy() if self.persistent_cache else {}

        with bz2.open(cache_path, "wb") as f:
            pickle.dump(data, f)

        log.success(f"Saved cache in {time.time() - start:.2f} seconds")
        self.last_save = time.time()
        del data

    @log.catch
    def load_cache(self, key_index: Optional[int] = None):
        """Load cache from disk into persistent cache."""
        cache_path = os.path.join(VID_CACHE, self.key_layout_str, f"{self.video_md5}.cache")
        if not os.path.exists(cache_path):
            return
        
        _time = time.time()
        try:
            with ibz2.open(cache_path, parallelization=os.cpu_count()) as f:
                self.persistent_cache = pickle.load(f)
            log.success(f"Loaded cache in {time.time() - _time:.2f} seconds")
        except Exception as e:
            os.remove(cache_path)
            log.error(f"Failed to load cache: {e}")
            return

    def is_cache_complete(self) -> bool:
        """Check if the persistent cache (disk-backed) is complete."""
        if self.n_frames != len(self.persistent_cache):
            return False
        
        for key in self.persistent_cache:
            if len(self.persistent_cache[key]) != self.key_count:
                return False

        return True
    
    def release_capture(self) -> None:
        """Release the video capture object."""
        if hasattr(self, 'cap') and self.cap is not None:
            self.cap.release()
    
    def get_cache_stats(self) -> Dict[str, any]:
        """Get cache statistics for monitoring."""
        lru_stats = self.cache.get_stats()
        return {
            "lru_cache": lru_stats,
            "persistent_cache_frames": len(self.persistent_cache),
            "total_frames": self.n_frames,
            "cache_complete": self.is_cache_complete()
        }
    
    def close(self) -> None:
        """Clean up resources."""
        with self.lock:
            # Release video capture
            self.release_capture()
            
            # Clear LRU cache (which will close images)
            self.cache.clear()

            # Close persistent cache images
            if self.persistent_cache:
                for frame_tiles in self.persistent_cache.values():
                    for tile in frame_tiles:
                        if hasattr(tile, 'close'):
                            tile.close()
                self.persistent_cache.clear()

            # Clear last tiles
            if self.last_tiles:
                for tile in self.last_tiles:
                    if hasattr(tile, 'close'):
                        tile.close()
                self.last_tiles.clear()

        log.debug("BackgroundVideoCache cleaned up")
    
    def __del__(self):
        """Ensure cleanup when object is destroyed."""
        try:
            self.close()
        except:
            pass  # Ignore errors during cleanup