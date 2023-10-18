import threading
import time
from loguru import logger as log

class ScreenSaver:
    def __init__(self, deck_controller: "DeckController"):
        self.deck_controller = deck_controller

        # Init vars
        self.original_background_video_task = None
        self.original_video_tasks = None
        self.original_key_images = None
        self.enable = False
        self.inactive_time = 3 # Default time
        self.active = False
        self.media_path = None

        # Time when last key state changed
        self.last_key_change_time = time.time()

        # Start thread
        thread = threading.Thread(target=self.thread_method)
        thread.start()

    @log.catch
    def thread_method(self):
        # time.sleep(100)
        while True:
            if not self.enable or self.media_path == None:
                time.sleep(0.1)
                continue

            print("check")
        
            if not self.active:
                passed_time = time.time() - self.last_key_change_time
                if passed_time > self.inactive_time:
                    log.info("Activating screen saver")
                    self.active = True
                    # Activate screen saver
                    self.show()

            time.sleep(0.5)

    def show(self):
        self.original_background_video_task = self.deck_controller.media_handler.background_video_task
        self.original_video_tasks = self.deck_controller.media_handler.video_tasks
        self.original_key_images = self.deck_controller.key_images

        # Reset original background video tasks
        self.deck_controller.media_handler.background_video_task = {}
        self.deck_controller.media_handler.video_tasks = {}
        self.deck_controller.key_images = [None]*self.deck_controller.deck.key_count()
        # self.deck_controller.media_handler.only_background = True
        # Give the handler some time to finish frame
        # time.sleep(0.1)
            
        self.deck_controller.set_background(media_path=self.media_path)

    def hide(self):
        self.active = False
        self.deck_controller.media_handler.background_video_task = self.original_background_video_task
        self.deck_controller.media_handler.video_tasks = self.original_video_tasks
        self.deck_controller.key_images = self.original_key_images

        # Reload
        self.deck_controller.reload_keys(skip_gifs=False)


    def on_key_change(self):
        self.last_key_change_time = time.time()
        if self.active:
            # Deactivate screen saver
            self.hide()