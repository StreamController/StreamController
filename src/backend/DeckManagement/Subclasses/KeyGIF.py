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
from typing import TYPE_CHECKING

from PIL import Image, ImageSequence

from src.backend.DeckManagement.Subclasses.SingleKeyAsset import SingleKeyAsset

if TYPE_CHECKING:
    from src.backend.DeckManagement.DeckController import ControllerKey


class KeyGIF(SingleKeyAsset):
    def __init__(self, controller_key: "ControllerKey", gif_path: str, fps: int = 30, loop: bool = True):
        super().__init__(controller_key)
        self.gif_path = gif_path
        self.fps = fps
        self.loop = loop

        self.active_frame: int = -1

        self.gif = Image.open(self.gif_path)
        self.frames = []
        self.frame_delays = []
        
        # Extract frames and their delays
        for frame in ImageSequence.Iterator(self.gif):
            self.frames.append(frame.convert("RGBA"))
            # Get frame delay from GIF metadata (in milliseconds)
            # Default to 100ms (10fps) if no delay specified
            delay = self.gif.info.get('duration', 100)
            # Some GIFs use delay in centiseconds, convert to milliseconds
            if delay < 50:
                delay *= 10
            self.frame_delays.append(delay)

    def get_next_frame(self) -> Image.Image:
        self.active_frame += 1

        if self.active_frame >= len(self.frames):
            if self.loop:
                self.active_frame = 0
            else:
                self.active_frame = len(self.frames) - 1

        return self.frames[self.active_frame]
    
    def get_frame_delay(self) -> float:
        """Get delay for current frame in seconds"""
        if self.active_frame < 0 or self.active_frame >= len(self.frame_delays):
            return 1.0 / self.fps  # Fallback to fps-based timing
        return self.frame_delays[self.active_frame] / 1000.0  # Convert ms to seconds
    
    def get_raw_image(self) -> Image.Image:
        return self.get_next_frame()
    
    def close(self) -> None:
        self.gif = None
        self.frames = None
        self.frame_delays = None
        del self.gif
        del self.frames
        del self.frame_delays
