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
import threading
import os

# Import own modules
import src.backend.DeckManagement.Subclasses.Video as Video
from src.backend.DeckManagement.ImageHelpers import *
from src.backend.DeckManagement.Subclasses.KeyVideo import KeyVideo
from src.backend.DeckManagement.Subclasses.BackgroundVideo import BackgroundVideo
from src.backend.DeckManagement.Subclasses.DeckMediaThread import DeckMediaThread

class DeckMediaHandler():
    def __init__(self, deck_controller):
        self.deck_controller = deck_controller
        self.deck = deck_controller.deck

        self.image_tasks = []
        self.video_tasks = {}
        self.background_video_task = {}

        self.thread = DeckMediaThread(self)
        self.thread.start()

        self.background_playing = False

    def add_image_task(self, key, native_image):
        self.image_tasks.append((key, native_image))

    @log.catch
    def add_video_task(self, key, video_path, loop=True, fps=30):
        def add_video_task_thread(self):
            self.video_tasks[key] = {}
            self.video_tasks[key]["frames"] = KeyVideo(self.deck_controller.deck, video_path).frames
            self.video_tasks[key]["loop"] = loop
            self.video_tasks[key]["fps"] = fps
            self.video_tasks[key]["active_frame"] = -1
        threading.Thread(target=add_video_task_thread, args=(self,)).start()

    @log.catch
    def set_background(self, media_path, loop=True, fps=30):
        def set_background_thread(self):
            if os.path.splitext(media_path)[1] in [".png", ".jpg", ".jpeg"]:
                # Background is an image
                self.deck_controller.background_key_tiles = create_wallpaper_image_array(deck=self.deck_controller.deck, image_filename=media_path)
                self.deck_controller.reload_keys(skip_gifs=True)
            else:
                # Background is a video
                bg_video = BackgroundVideo(self.deck_controller.deck, media_path)
                self.background_video_task["frames"] = bg_video.frames
                self.background_video_task["loop"] = loop
                self.background_video_task["fps"] = fps
                self.background_video_task["active_frame"] = -1
        threading.Thread(target=set_background_thread, args=(self,)).start()