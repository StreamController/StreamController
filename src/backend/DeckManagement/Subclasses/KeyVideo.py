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

        # GIF timing state: track elapsed ms to honour per-frame delays
        self._gif_elapsed_ms: float = 0.0
        self._gif_last_tick: int = -1

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
        """Advance GIF playback using per-frame delays from GIF metadata."""
        try:
            media_player_fps = self.controller_input.deck_controller.media_player.FPS
            tick = self.controller_input.media_ticks

            if self._gif_last_tick < 0:
                self.active_frame = 0
                self._gif_last_tick = tick
                return self.video_cache.get_frame(0)

            ticks_elapsed = max(0, tick - self._gif_last_tick)
            self._gif_elapsed_ms += ticks_elapsed * (1000.0 / max(media_player_fps, 1))
            self._gif_last_tick = tick

            delay = self.video_cache.get_frame_delay(self.active_frame)
            if self._gif_elapsed_ms >= delay:
                self._gif_elapsed_ms = 0.0
                next_frame = self.active_frame + 1
                if next_frame >= self.video_cache.n_frames:
                    if self.loop:
                        next_frame = 0
                    else:
                        next_frame = self.video_cache.n_frames - 1
                self.active_frame = next_frame

            return self.video_cache.get_frame(self.active_frame)
        except Exception:
            return self.video_cache.get_frame(0)

    def get_raw_image(self) -> Image.Image:
        return self.get_next_frame()
