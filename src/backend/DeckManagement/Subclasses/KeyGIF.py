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

"""GIF assets with playback timed from Pillow's per-frame durations."""

from bisect import bisect_right
from itertools import accumulate
import time

from PIL import Image, ImageSequence

from src.backend.DeckManagement.Subclasses.SingleKeyAsset import SingleKeyAsset


class KeyGIF(SingleKeyAsset):
    def __init__(self, controller_key, gif_path: str, fps: int = 30, loop: bool = True):
        super().__init__(controller_key)
        self.gif_path = gif_path
        self.fps = fps
        self.loop = loop
        self.active_frame = -1
        self._start_time_ns = None
        self.frames = []
        self.frame_delays = []

        with Image.open(gif_path) as gif:
            for frame in ImageSequence.Iterator(gif):
                self.frames.append(frame.convert("RGBA"))
                # Pillow has already converted GIF centiseconds to milliseconds.
                # Use 100 ms for unspecified/zero delays, never scale valid ones.
                self.frame_delays.append(frame.info.get("duration", 100) or 100)

        self._frame_end_times = list(accumulate(self.frame_delays))
        self._duration_ms = self._frame_end_times[-1]

    def _get_frame_index(self) -> int:
        if self._start_time_ns is None:
            return 0

        elapsed_ms = (time.monotonic_ns() - self._start_time_ns) // 1_000_000
        if self.loop:
            elapsed_ms %= self._duration_ms
        elif elapsed_ms >= self._duration_ms:
            return len(self.frames) - 1

        # Select directly from the timeline so late ticks neither slow playback
        # nor require decoding every missed frame after a long pause.
        return bisect_right(self._frame_end_times, elapsed_ms)

    def is_frame_due(self) -> bool:
        return self._get_frame_index() != self.active_frame

    def get_next_frame(self) -> Image.Image:
        if self._start_time_ns is None:
            self._start_time_ns = time.monotonic_ns()
        self.active_frame = self._get_frame_index()
        return self.frames[self.active_frame]

    def get_frame_delay(self) -> float:
        """Get the current frame's duration in seconds."""
        if self.active_frame < 0:
            return 1.0 / self.fps
        return self.frame_delays[self.active_frame] / 1000.0

    def get_raw_image(self) -> Image.Image:
        return self.get_next_frame()

    def close(self) -> None:
        for frame in self.frames:
            frame.close()
        self.frames.clear()
        self.frame_delays.clear()
