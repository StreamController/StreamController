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
from loguru import logger as log
import cv2
from PIL import Image, ImageSequence
from StreamDeck.ImageHelpers import PILHelper

# Import own modules
from src.backend.DeckManagement.Subclasses.Video import Video
from src.backend.DeckManagement.HelperMethods import *

class KeyVideo(Video):
    @log.catch
    def __init__(self, deck, video_path):
        super().__init__()
        self.deck = deck
        hash = sha256(video_path)
        file_name = f"{hash}-single.cache"
        # Check if video has already been cached:
        if file_in_dir(file_name, "cache"):
            print("from cache")
            self.load_from_cache(file_name)

            log.success(f"Loaded {len(self.frames)} frames from cache: {video_path}")
        else:
            print("gen")
            self.load_from_file(video_path)
            self.save_to_cache(file_name)
        
            log.success(f"Loaded {len(self.frames)} frames from disk: {video_path}")

    @log.catch
    def load_from_file(self, video_path):
        if os.path.splitext(video_path)[1] in [".gif", ".GIF"]:
            log.info(f"Loading gif {video_path}")
            self.load_gif(video_path)
        else:
            log.info(f"Loading video {video_path}")
            self.load_video(video_path)

    @log.catch
    def load_video(self, video_path):
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
            scaled_pillow_image = PILHelper.create_scaled_image(self.deck, image=pillow_image)
            self.frames.append(scaled_pillow_image)

    @log.catch
    def load_gif(self, gif_path):
        # This is the same as load_video but with transparency support
        gif = Image.open(gif_path)
        for frame in ImageSequence.Iterator(gif):
            frame = frame.convert("RGBA")
            self.frames.append(frame)