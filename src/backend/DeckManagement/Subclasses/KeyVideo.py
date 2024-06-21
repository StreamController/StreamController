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

        self.video_cache = VideoFrameCache(video_path, size=self.controller_input.get_image_size())

        self.active_frame: int = -1

    def get_next_frame(self) -> Image:
        self.active_frame += 1

        if self.active_frame >= self.video_cache.n_frames:
            if self.loop:
                self.active_frame = 0
        
        return self.video_cache.get_frame(self.active_frame)
    
    def get_raw_image(self) -> Image.Image:
        return self.get_next_frame()
     