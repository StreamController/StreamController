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
import threading
from time import time, sleep


class DeckMediaThread(threading.Thread):
    FRAMES_PER_SECOND = 30
    def __init__(self, media_handler):
        super().__init__()
        self.media_handler = media_handler


    @log.catch
    def run(self):
        log.info("Starting DeckMediaThread")

        self.ticks = 0
        while True: 
            # Handling video requests
            tick_start_time = time()
            video_tasks = dict(self.media_handler.video_tasks.items()) # Use list to avoid runtime error for changing dict during iteration 

            with self.media_handler.deck_controller.deck:
                if not self.media_handler.only_background:
                    # Handle key videos
                    self.handle_videos(video_tasks)

                # Hande background video
                self.handle_background_video()

                if not self.media_handler.only_background:
                    # Handling image requests
                    self.handle_image_requests()
        
            sleep_time = (1 / self.FRAMES_PER_SECOND)-(time() - tick_start_time)
            sleep(max(sleep_time, 0))

            self.ticks += 1

    @log.catch
    def handle_image_requests(self):
        for i in range(len(self.media_handler.image_tasks)):
            if i > len(self.media_handler.image_tasks) - 1:
                break
            key_index, native_image, ui_image = self.media_handler.image_tasks[i]
            if ui_image != None:
                self.media_handler.deck_controller.set_ui_key(key_index, ui_image)
            
            self.media_handler.deck_controller.deck.set_key_image(key_index, native_image)
            self.media_handler.image_tasks.pop(i)
            
    @log.catch
    def handle_videos(self, video_tasks):
        for key in video_tasks:
            if "frames" not in video_tasks[key]:
                continue
            if len(video_tasks[key]["frames"]) == 0 or "active_frame" not in video_tasks[key]:
                continue

            # Check if this video should get updated now
            each_n_frame = self.FRAMES_PER_SECOND / video_tasks[key]["fps"]
            if self.ticks % each_n_frame != 0:
                continue

            video_tasks[key]["active_frame"] += 1

            if video_tasks[key]["active_frame"] >= len(video_tasks[key]["frames"]):
                if video_tasks[key]["loop"] == False:
                    continue
                video_tasks[key]["active_frame"] = 0

            image = video_tasks[key]["frames"][video_tasks[key]["active_frame"]]            
            shrink = self.media_handler.deck_controller.deck.key_states()[key]
            self.media_handler.deck_controller.set_image(key=key, labels=None, image=image, add_background=True, bypass_task=True, shrink=shrink)
            self.media_handler.deck_controller.set_ui_key(key, image=image, force_add_background=True)
            # TODO: add label support
    @log.catch
    def handle_background_video(self):
        if self.media_handler.background_video_task == None:
            return
        if "active_frame" not in self.media_handler.background_video_task:
            return
        if "frames" not in self.media_handler.background_video_task:
            return
        
        self.media_handler.background_video_task["active_frame"] += 1
        if self.media_handler.background_video_task["active_frame"] >= len(self.media_handler.background_video_task["frames"]):
            if self.media_handler.background_video_task["loop"] == False:
                self.media_handler.background_playing = False
                return
            self.media_handler.background_video_task["active_frame"] = 0
        
        each_n_frame = self.FRAMES_PER_SECOND / self.media_handler.background_video_task["fps"]
        if self.ticks % each_n_frame != 0:
            return
        
        self.media_handler.background_playing = True

        tiles = self.media_handler.background_video_task["frames"][self.media_handler.background_video_task["active_frame"]]
        self.media_handler.deck_controller.background_key_tiles = tiles
        self.media_handler.deck_controller.reload_keys(skip_gifs=True, update_ui=True)
