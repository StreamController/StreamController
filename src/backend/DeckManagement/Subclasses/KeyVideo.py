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
from decord import VideoReader
from decord import cpu, gpu

# Import own modules
from src.backend.DeckManagement.Subclasses.Video import Video
from src.backend.DeckManagement.HelperMethods import *

class KeyVideo(Video):
    @log.catch
    def __init__(self, deck_media_handler, deck, video_path, progress_id=None):
        super().__init__()
        self.deck = deck
        self.deck_media_handler = deck_media_handler
        self.progress_id = progress_id
        hash = sha256(video_path)
        file_name = f"{hash}-single.cache"
        # Check if video has already been cached:
        if file_in_dir(file_name, "cache"):
            self.load_from_cache(file_name)

            log.success(f"Loaded {len(self.frames)} frames from cache: {video_path}")
            self.deck_media_handler.progress_dir[progress_id] = 1
        else:
            self.load_from_file(video_path)
            self.save_to_cache(file_name)
        
            log.success(f"Loaded {len(self.frames)} frames from disk: {video_path}")
            self.deck_media_handler.progress_dir[progress_id] = 1

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
            with open(video_path, "rb") as f:
                vr = VideoReader(f, ctx=cpu(0))
                for frame in vr:
                    image = Image.fromarray(frame.asnumpy())
                    scaled_image = PILHelper.create_scaled_image(self.deck, image)
                    self.frames.append(scaled_image)
                    # update progress
                    self.deck_media_handler.progress_dir[self.progress_id] = float(len(self.frames)) / len(vr)

    @log.catch
    def load_gif(self, gif_path):
        # This is the same as load_video but with transparency support
        gif = Image.open(gif_path)
        iterator = ImageSequence.Iterator(gif)
        n_frames = 0
        for frame in iterator:
            n_frames += 1 #TODO: Find a better way to do this
        iterator = ImageSequence.Iterator(gif)
        for frame in iterator:
            frame = frame.convert("RGBA")
            self.frames.append(frame)
            # update progress
            self.progress_var = len(self.frames) // n_frames