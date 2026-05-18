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
import time

from src.backend.DeckManagement.Subclasses.SingleKeyAsset import SingleKeyAsset
from src.backend.DeckManagement.Subclasses.key_video_cache import VideoFrameCache
from PIL import Image

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from src.backend.DeckManagement.DeckController import ControllerInput

class InputVideo(SingleKeyAsset):
    def __init__(self, controller_input: "ControllerInput", video_path: str, fps: int = 30, loop: bool = True):
        super().__init__(
            controller_input=controller_input,
        )
        self.video_path = video_path
        self.fps = fps
        self.loop = loop

        self.video_cache = VideoFrameCache.get_or_create(video_path, size=self.controller_input.get_image_size())

        self.active_frame: int = -1

        # GIF timing state: real-time based, independent of media player FPS
        self._gif_elapsed_ms: float = 0.0
        self._gif_last_ts: float = -1.0  # perf_counter timestamp in ms, -1 = not started

    def get_next_frame(self) -> Image:
        if self.video_cache._is_gif():
            return self._get_next_gif_frame()

        every_n_frames = self.controller_input.deck_controller.media_player.FPS // self.fps
        if self.controller_input.media_ticks % every_n_frames == 0:
            self.active_frame += 1

        if self.active_frame >= self.video_cache.n_frames:
            if self.loop:
                self.active_frame = 0

        return self.video_cache.get_frame(self.active_frame)

    def _get_next_gif_frame(self) -> Image:
        """Advance GIF playback using real-time elapsed ms and per-frame delays."""
        try:
            now_ms = time.perf_counter() * 1000.0

            if self._gif_last_ts < 0:
                self.active_frame = 0
                self._gif_last_ts = now_ms
                return self.video_cache.get_frame(0)

            self._gif_elapsed_ms += now_ms - self._gif_last_ts
            self._gif_last_ts = now_ms

            # Advance as many frames as the elapsed time requires.
            # The while loop handles catch-up when the media player was delayed.
            n_frames = self.video_cache.n_frames
            while True:
                delay = self.video_cache.get_frame_delay(self.active_frame)
                if self._gif_elapsed_ms < delay:
                    break
                self._gif_elapsed_ms -= delay
                next_frame = self.active_frame + 1
                if next_frame >= n_frames:
                    if self.loop:
                        next_frame = 0
                    else:
                        next_frame = n_frames - 1
                        self._gif_elapsed_ms = 0.0  # freeze on last frame
                        self.active_frame = next_frame
                        break
                self.active_frame = next_frame

            return self.video_cache.get_frame(self.active_frame)
        except Exception:
            return self.video_cache.get_frame(0)

    def get_raw_image(self) -> Image.Image:
        return self.get_next_frame()
