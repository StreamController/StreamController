"""
Author: Core447
Year: 2024

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
any later version.

This programm comes with ABSOLUTELY NO WARRANTY!

You should have received a copy of the GNU General Public License
along with this program. If not, see <https://www.gnu.org/licenses/>.
"""

import hashlib
import json
import os
import sys
import threading
import time
from PIL import Image, ImageOps
import cv2
from loguru import logger as log
import globals as gl

VID_CACHE = os.path.join(gl.DATA_PATH, "cache", "videos")


class VideoFrameCache:
    # Registry: same (video_path, size) → same instance, no double-loading.
    _registry: dict[tuple, "VideoFrameCache"] = {}
    _registry_lock = threading.Lock()

    # Per-key locks: ensure only one thread runs __init__ for a given key.
    # This prevents two threads from writing to the same cache files
    # simultaneously (which would corrupt PNGs and cause segfaults in PIL).
    _init_locks: dict[tuple, threading.Lock] = {}
    _init_locks_lock = threading.Lock()

    @classmethod
    def get_or_create(cls, video_path: str, size: tuple[int, int]) -> "VideoFrameCache":
        key = (os.path.abspath(video_path), size)

        # Fast path: already in registry (no I/O needed).
        with cls._registry_lock:
            existing = cls._registry.get(key)
            if existing is not None:
                return existing

        # Acquire a per-key lock so that only one thread runs __init__ for
        # this (path, size) at a time.  The global _registry_lock is NOT
        # held during __init__, so other keys are never blocked.
        with cls._init_locks_lock:
            if key not in cls._init_locks:
                cls._init_locks[key] = threading.Lock()
            key_lock = cls._init_locks[key]

        with key_lock:
            # Re-check: another thread may have completed init while we waited.
            with cls._registry_lock:
                existing = cls._registry.get(key)
                if existing is not None:
                    return existing

            instance = cls(video_path, size)

            with cls._registry_lock:
                cls._registry[key] = instance
            return instance

    def __init__(self, video_path: str, size: tuple[int, int]):
        self.video_path = video_path
        self.size = size

        # Background thread writes, main thread reads.
        # Individual dict get/set is GIL-atomic in CPython.
        self.cache: dict[int, Image.Image] = {}
        self.frame_delays: list[int] = []
        self.n_frames = 1  # updated in __init__ once we know the real count

        self.last_decoded_frame = None
        self.last_frame_index = -1
        self.lock = threading.Lock()  # guards cv2 capture only

        self.do_caching = gl.settings_manager.get_app_settings().get("performance", {}).get("cache-videos", True)
        self.do_caching = True

        # O(1) cache key — just a stat() call, no file read.
        self.video_md5 = self._fast_cache_key()

        if not self._is_gif():
            self.cap = cv2.VideoCapture(video_path)
            self.n_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        else:
            # Render frame 0 synchronously: gives every button a static preview
            # immediately, before any background thread runs.
            try:
                with Image.open(video_path) as gif:
                    self.n_frames = getattr(gif, "n_frames", 1)
                    gif.seek(0)
                    frame0 = ImageOps.fit(gif.convert("RGBA"), self.size, Image.Resampling.LANCZOS)
                self.cache[0] = frame0
            except Exception as e:
                log.warning(f"Could not render GIF preview for {video_path}: {e}")

        threading.Thread(
            target=self._load_in_background,
            daemon=True,
            name=f"vid-cache-{os.path.basename(video_path)}",
        ).start()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _fast_cache_key(self) -> str:
        stat = os.stat(self.video_path)
        return hashlib.md5(f"{stat.st_mtime_ns}_{stat.st_size}".encode()).hexdigest()

    def _is_gif(self) -> bool:
        return os.path.splitext(self.video_path)[1].lower() == ".gif"

    def _cache_dir(self, key_index: int = None) -> str:
        ext_part = f"{self.size[0]}x{self.size[1]}"
        if key_index is None:
            return os.path.join(VID_CACHE, "single_key", self.video_md5, ext_part)
        return os.path.join(VID_CACHE, f"key: {key_index}", self.video_md5, ext_part, str(key_index))

    def _frame_ext(self) -> str:
        return "png" if self._is_gif() else "jpg"

    def _delays_path(self) -> str:
        return os.path.join(self._cache_dir(), "delays.json")

    # ------------------------------------------------------------------
    # Background loading
    # ------------------------------------------------------------------

    def _load_in_background(self):
        if self._is_gif():
            self._load_gif_background()
        else:
            self._load_video_background()

    def _load_gif_background(self):
        """Build full GIF cache. Frame 0 is already in self.cache from __init__."""
        try:
            n = self.n_frames

            # Phase 1 — persist frame 0 to disk if not already there.
            if 0 in self.cache and self.do_caching:
                self._write_cache_frame(self.cache[0], 0)

            # Phase 2 — load delays: from disk cache (fast) or from GIF (slow, once).
            delays_path = self._delays_path()
            if os.path.exists(delays_path):
                try:
                    with open(delays_path) as f:
                        self.frame_delays = json.load(f)
                except Exception:
                    self.frame_delays = [100] * n
            else:
                self.frame_delays = self._read_gif_delays(n)
                if self.do_caching:
                    try:
                        os.makedirs(os.path.dirname(delays_path), exist_ok=True)
                        with open(delays_path, "w") as f:
                            json.dump(self.frame_delays, f)
                    except Exception as e:
                        log.warning(f"Could not save delays cache: {e}")

            # Phase 3 — load remaining frames from disk cache.
            self._load_cache_from_disk()

            # Phase 4 — decode any frames still missing (first run only).
            if not self.is_cache_complete():
                with Image.open(self.video_path) as gif:
                    for i in range(n):
                        if i in self.cache:
                            continue
                        try:
                            gif.seek(i)
                            frame = ImageOps.fit(gif.convert("RGBA"), self.size, Image.Resampling.LANCZOS)
                            if self.do_caching:
                                self._write_cache_frame(frame, i)
                            self.cache[i] = frame
                        except Exception as e:
                            log.warning(f"Failed to decode GIF frame {i}: {e}")

            if self.is_cache_complete():
                log.info(f"GIF cache complete ({n} frames): {os.path.basename(self.video_path)}")
            else:
                log.warning(f"GIF cache incomplete ({len(self.cache)}/{n}): {os.path.basename(self.video_path)}")

        except Exception as e:
            log.error(f"Failed to load GIF {self.video_path}: {e}")

        log.trace(f"Cache memory: {sys.getsizeof(self.cache) / 1024 / 1024:.2f} MB")

    def _read_gif_delays(self, n: int) -> list[int]:
        """Seek through GIF once to read per-frame delays. Slow — called once, result cached to disk."""
        try:
            delays = []
            with Image.open(self.video_path) as gif:
                for i in range(n):
                    gif.seek(i)
                    delays.append(gif.info.get("duration", 0))
            last_valid = 100
            for i, d in enumerate(delays):
                if d <= 0:
                    delays[i] = last_valid
                else:
                    last_valid = d
            return delays
        except Exception:
            return [100] * n

    def _load_video_background(self):
        self._load_cache_from_disk()
        if self.is_cache_complete():
            log.info("Video cache complete. Closing capture.")
            with self.lock:
                self.cap.release()
        else:
            log.info("Video cache incomplete. Keeping capture open.")
        log.trace(f"Cache memory: {sys.getsizeof(self.cache) / 1024 / 1024:.2f} MB")

    # ------------------------------------------------------------------
    # Frame access (main / media-player thread)
    # ------------------------------------------------------------------

    def get_frame_delay(self, frame_index: int) -> int:
        if self.frame_delays and 0 <= frame_index < len(self.frame_delays):
            return self.frame_delays[frame_index]
        return 100

    def get_frame(self, n: int):
        if self._is_gif():
            return self._get_gif_frame(n)

        n = min(n, self.n_frames - 1)
        if self.is_cache_complete():
            return self.cache.get(n)

        if n in self.cache:
            return self.cache[n]

        if n < self.last_frame_index:
            with self.lock:
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, n)
            self.last_frame_index = n - 1

        while self.last_frame_index < n:
            with self.lock:
                success, frame = self.cap.read()
            if not success:
                break
            self.last_frame_index += 1
            pil_image = ImageOps.fit(
                Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)),
                self.size, Image.Resampling.LANCZOS,
            )
            self.last_decoded_frame = pil_image
            if self.do_caching:
                self.cache[self.last_frame_index] = pil_image
                self._write_cache_frame(pil_image, self.last_frame_index)

        return self.cache.get(n, self.last_decoded_frame)

    def _get_gif_frame(self, n: int):
        n = min(n, self.n_frames - 1)
        frame = self.cache.get(n)
        if frame is not None:
            return frame
        # Still loading: return frame 0 as static preview
        return self.cache.get(0)

    # ------------------------------------------------------------------
    # Disk cache I/O
    # ------------------------------------------------------------------

    def _write_cache_frame(self, image: Image.Image, frame_index: int, key_index: int = None):
        path = os.path.join(self._cache_dir(key_index), f"{frame_index}.{self._frame_ext()}")
        if os.path.isfile(path):
            return
        os.makedirs(os.path.dirname(path), exist_ok=True)
        image.save(path)

    def _load_cache_from_disk(self, key_index: int = None):
        ext = self._frame_ext()
        path = self._cache_dir(key_index)
        if not os.path.exists(path):
            return
        start = time.time()
        for file in os.listdir(path):
            if os.path.splitext(file)[1] != f".{ext}":
                continue
            idx = int(file.split(".")[0])
            if idx in self.cache:
                continue
            try:
                with Image.open(os.path.join(path, file)) as img:
                    self.cache[idx] = img.copy()
            except Exception as e:
                log.warning(f"Failed to load cached frame {file}: {e}")
        log.info(f"Loaded disk cache in {time.time() - start:.2f}s ({len(self.cache)} frames)")

    # ------------------------------------------------------------------
    # Legacy public API
    # ------------------------------------------------------------------

    def write_cache(self, image: Image.Image, frame_index: int, key_index: int = None):
        self._write_cache_frame(image, frame_index, key_index)

    def load_cache(self, key_index: int = None):
        self._load_cache_from_disk(key_index)

    def get_video_hash(self) -> str:
        sha1sum = hashlib.md5()
        with open(self.video_path, "rb") as f:
            block = f.read(2**16)
            while block:
                sha1sum.update(block)
                block = f.read(2**16)
        return sha1sum.hexdigest()

    def release(self):
        with self.lock:
            if hasattr(self, "cap") and self.cap is not None:
                self.cap.release()

    def is_cache_complete(self) -> bool:
        return len(self.cache) == self.n_frames
