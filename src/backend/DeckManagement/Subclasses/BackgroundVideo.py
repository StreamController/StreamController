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
# Import Python modules
import cv2
from loguru import logger as log
from PIL import Image

# Import own modules
from src.backend.DeckManagement.Subclasses.Video import Video
from src.backend.DeckManagement.HelperMethods import *
from src.backend.DeckManagement.ImageHelpers import *

class BackgroundVideo(Video):
    @log.catch
    def __init__(self, deck_media_handler, deck, video_path, progress_id=None):
        super().__init__()
        self.progress_id = progress_id
        self.deck_media_handler = deck_media_handler
        hash = sha256(video_path)
        x, y = deck.key_layout()
        file_name = f"{hash}-{x}x{y}.cache"
        # Check if video has already been cached:
        if file_in_dir(file_name, "cache"):
            print("from cache")
            self.load_from_cache(file_name)
            self.deck_media_handler.progress_dir[progress_id] = 1
        else:
            self.load_from_video(deck, video_path)
            self.save_to_cache(file_name)
            self.deck_media_handler.progress_dir[progress_id] = 1

    @log.catch
    def load_from_video(self, deck, video_path):
        self.video = cv2.VideoCapture(video_path)

        n_frames = int(self.video.get(cv2.CAP_PROP_FRAME_COUNT))

        while True:
            success, frame = self.video.read()
            if not success:
                if len(self.frames) < n_frames:
                    log.error("Failed to load frames for video: {}".format(video_path))
                break
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            pillow_image = Image.fromarray(rgb_frame)
            self.frames.append(create_wallpaper_image_array(deck, image=pillow_image))

            # update progress
            self.deck_media_handler.progress_dir[self.progress_id] = float(len(self.frames)) / n_frames