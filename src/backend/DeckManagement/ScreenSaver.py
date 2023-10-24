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
        self.original_video_tasks = None
        self.original_key_images = None
        self.original_brightness = None
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
        if self.enable:
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
        else:
            # Start time if not already running
            if not self.timer.is_alive:
                self.timer.start()

    def set_brightness(self, brightness):
        if self.showing:
            self.original_brightness = self.deck_controller.get_brightness()
            self.deck_controller.set_brightness(brightness)
            # Set background if old brightness was 0 and it therefore was not set
            if brightness > 0 and self.brightness == 0:
                self.deck_controller.set_background(media_path=self.media_path, bypass_task=True)
        self.brightness = brightness

    def on_timer_end(self):
        self.showing = True
        self.show()

    def show(self):
        self.deck_controller.media_handler.thread.pause_work = True
        self.original_background_video_task = self.deck_controller.media_handler.background_video_task
        self.original_background_key_tiles = self.deck_controller.background_key_tiles
        self.original_video_tasks = self.deck_controller.media_handler.video_tasks
        self.original_key_images = self.deck_controller.key_images
        self.original_brightness = self.deck_controller.get_brightness()

        # Change brightness
        self.deck_controller.set_brightness(self.brightness)

        # Reset original background video tasks
        self.deck_controller.media_handler.background_video_task = {}
        self.deck_controller.media_handler.video_tasks = {}
        self.deck_controller.media_handler.image_tasks = []
        # self.deck_controller.media_handler.video_tasks = {}
        self.deck_controller.key_images = [None]*self.deck_controller.deck.key_count()

        # wait
        while self.deck_controller.media_handler.thread.working:
            pass

        # time.sleep(0.5)
        if self.brightness > 0:
            # No need for changing background if brightness is 0
            print("Change background")
            self.deck_controller.set_background(media_path=self.media_path, bypass_task=True)
            print("Finished changing background")

        # time.sleep(0.2)

        self.deck_controller.media_handler.thread.pause_work = False

    def hide(self):
        self.showing = False
        self.set_time(self.time_delay)
        self.deck_controller.media_handler.background_video_task = self.original_background_video_task
        self.deck_controller.background_key_tiles = self.original_background_key_tiles
        self.deck_controller.media_handler.video_tasks = self.original_video_tasks
        self.deck_controller.key_images = self.original_key_images
        self.deck_controller.set_brightness(self.original_brightness)

        # Reload
        self.deck_controller.reload_keys(skip_gifs=False)


    def on_key_change(self):
        self.last_key_change_time = time.time()
        if self.showing:
            # Deactivate screen saver
            self.hide()
        else:
            self.set_time(self.time_delay)