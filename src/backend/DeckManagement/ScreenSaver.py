import threading
import time
from loguru import logger as log
import multiprocessing

class ScreenSaver:
    def __init__(self, deck_controller: "DeckController"):
        self.deck_controller = deck_controller

        # Init vars
        self.original_background_video_task = None
        self.original_background_key_tiles = None
        self.original_video_tasks = None
        self.original_key_images = None
        self.enable = False
        self.time_delay = None # Default time
        self.showing = False
        self.media_path = None

        # Time when last key state changed
        self.last_key_change_time = time.time()

    def set_time(self, time_delay):
        # return
        self.time_delay = time_delay
        if hasattr(self, "timer"):
            self.timer.cancel()
        self.timer = threading.Timer(time_delay, self.on_timer_end)
        self.timer.start()

    def set_enable(self, enable):
        # return
        self.enable = enable

        # Hide if showing and enable == False
        if self.showing and not enable:
            self.hide()

        if not hasattr(self, "timer"):
            return
        
        # Stop timer if enable == False
        if not enable:
            self.timer.cancel()

        # Start time if not already running
        if not self.timer.is_alive:
            self.timer.start()

    def on_timer_end(self):
        self.showing = True
        self.show()

    def show(self):
        self.original_background_video_task = self.deck_controller.media_handler.background_video_task
        self.original_background_key_tiles = self.deck_controller.background_key_tiles
        self.original_video_tasks = self.deck_controller.media_handler.video_tasks
        self.original_key_images = self.deck_controller.key_images

        # Reset original background video tasks
        self.deck_controller.media_handler.background_video_task = {}
        # self.deck_controller.media_handler.video_tasks = {}
        self.deck_controller.key_images = [None]*self.deck_controller.deck.key_count(()
            
        self.deck_controller.set_background(media_path=self.media_path)

    def hide(self):
        self.showing = False
        self.set_time(self.time_delay)
        self.deck_controller.media_handler.background_video_task = self.original_background_video_task
        self.deck_controller.background_key_tiles = self.original_background_key_tiles
        self.deck_controller.media_handler.video_tasks = self.original_video_tasks
        self.deck_controller.key_images = self.original_key_images

        # Reload
        self.deck_controller.reload_keys(skip_gifs=False)


    def on_key_change(self):
        self.last_key_change_time = time.time()
        if self.showing:
            # Deactivate screen saver
            self.hide()
        else:
            self.set_time(self.time_delay)