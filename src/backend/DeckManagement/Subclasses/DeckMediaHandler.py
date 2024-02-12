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
import time
import uuid

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

        self.only_background = False

        self.thread = DeckMediaThread(self)
        self.thread.start()

        self.background_playing = False

        self.progress_dir = {}

    def add_image_task(self, key, native_image, ui_image = None):
        self.image_tasks.append((key, native_image, ui_image))

    @log.catch
    def add_video_task(self, key, video_path, loop=True, fps=30, labels=None):
        def add_video_task_thread(self, id):
            self.video_tasks[key] = {}
            self.video_tasks[key]["frames"] = KeyVideo(self, self.deck_controller.deck, video_path, progress_id=id).frames
            self.video_tasks[key]["loop"] = loop
            self.video_tasks[key]["fps"] = fps
            self.video_tasks[key]["active_frame"] = -1
            self.video_tasks[key]["labels"] = labels


        # Generate unique id to track processing progress
        id = str(uuid.uuid4())
        self.progress_dir[id] = 0
        log.info("Starting thread: add_video_task")
        threading.Thread(target=add_video_task_thread, args=(self, id)).start()
        return id


    @log.catch
    def set_background(self, media_path, loop=True, fps=30, reload=True, bypass_task=False):
        id = str(uuid.uuid4())
        self.progress_dir[id] = 0   
        if media_path is None:
            self.deck_controller.set_background_to_none()
            return

        if os.path.splitext(media_path)[1] in [".png", ".jpg", ".jpeg"]:
            # Remove background video
            self.background_video_task = {}
            # Background is an image
            image = Image.open(media_path)
            self.deck_controller.background_key_tiles = create_wallpaper_image_array(deck=self.deck_controller.deck, image=image)
            self.progress_dir[id] = 1
            if reload:
                # Reload deck
                self.deck_controller.reload_keys(skip_gifs=True, bypass_task=bypass_task)
                # Reload ui keys
                # self.deck_controller.reload_ui_keys()
        else:
            # Background is a video
            bg_video = BackgroundVideo(self, self.deck_controller.deck, media_path, progress_id=id)
            self.background_video_task["frames"] = bg_video.frames
            self.background_video_task["loop"] = loop
            self.background_video_task["fps"] = fps
            self.background_video_task["active_frame"] = -1
            self.progress_dir[id] = 1

        # Generate unique id to track processing progress
        return id
    
    def stop_all_tasks(self):
        self.image_tasks = []
        self.video_tasks = {}
        self.background_video_task = {}

        while self.thread.working:
            time.sleep(1/30)

    def delete(self):
        self.thread.pause_work = True
        self.stop_all_tasks()
        del self.thread