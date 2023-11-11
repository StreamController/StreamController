from src.backend.PluginManager.ActionBase import ActionBase
from src.backend.PluginManager.PluginBase import PluginBase

# Import gtk modules
import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw

import sys
import os
import threading
from datetime import timedelta
from loguru import logger as log
from obswebsocket import events

# Add plugin to sys.paths
sys.path.append(os.path.dirname(__file__))

from OBSController import OBSController

class ToggleRecord(ActionBase):
    ACTION_NAME = "Toggle Record"
    CONTROLS_KEY_IMAGE = True
    def __init__(self, deck_controller, page, coords):
        super().__init__(deck_controller=deck_controller, page=page, coords=coords)

    def on_ready(self):
        # Connect to obs if not connected
        if not self.PLUGIN_BASE.obs.connected:
            self.PLUGIN_BASE.obs.connect_to(host="localhost", port=4444, timeout=3, legacy=False)

        # Show current rec status
        self.show_current_rec_status()

        # Register signal
        self.PLUGIN_BASE.obs.register(self.on_state_change, events.RecordStateChanged)


    def on_state_change(self, message):
        state_string = message.datain["outputState"]
        state = 0
        if state_string == "OBS_WEBSOCKET_OUTPUT_STOPPED":
            state = 0
        elif state_string in ["OBS_WEBSOCKET_OUTPUT_STARTING", "OBS_WEBSOCKET_OUTPUT_STARTED", "OBS_WEBSOCKET_OUTPUT_RESUMED"]:
            state = 1
        elif state_string == "OBS_WEBSOCKET_OUTPUT_PAUSED":
            state = 2

        self.show_for_state(state)

    def show_current_rec_status(self, new_paused = False):
        active = self.PLUGIN_BASE.obs.get_record_status().datain["outputActive"]
        paused = self.PLUGIN_BASE.obs.get_record_status().datain["outputPaused"]
        if paused:
            self.show_for_state(2)
        elif active:
            self.show_for_state(1)
        else:
            self.show_for_state(0)

    def show_for_state(self, state: int):
        """
        0: Not Recording
        1: Recording
        2: Paused
        3: Stopping in progress
        """
        image = "record_inactive.png"
        if state == 0:
            self.set_bottom_label(None)
            image = "record_inactive.png"
        elif state == 1:
            self.show_rec_time()
            image = "record_active.png"
        elif state == 2:
            self.show_rec_time()
            image = "record_resume.png"

        self.set_key(media_path=os.path.join(self.PLUGIN_BASE.PATH, "assets", image))

    def on_key_down(self):
        self.PLUGIN_BASE.obs.toggle_record()

    def on_tick(self):
        self.show_rec_time()

    def show_rec_time(self):
        status = self.PLUGIN_BASE.obs.get_record_status()
        active = status.datain["outputActive"]
        if not active:
            self.set_bottom_label(None)
            return
        self.set_bottom_label(status.datain["outputTimecode"][:-4], font_size=16)

class RecPlayPause(ActionBase):
    ACTION_NAME = "Recording Play/Pause"
    CONTROLS_KEY_IMAGE = True
    def __init__(self, deck_controller, page, coords):
        super().__init__(deck_controller=deck_controller, page=page, coords=coords)

    def on_ready(self):
        # Connect to obs if not connected
        if not self.PLUGIN_BASE.obs.connected:
            self.PLUGIN_BASE.obs.connect_to(host="localhost", port=4444, timeout=3, legacy=False)

        # Show current rec status
        self.show_current_rec_status()

        # Register signal
        self.PLUGIN_BASE.obs.register(self.on_state_change, events.RecordStateChanged)


    def on_state_change(self, message):
        state_string = message.datain["outputState"]
        state = 0
        if state_string in ["OBS_WEBSOCKET_OUTPUT_RESUMED", "OBS_WEBSOCKET_OUTPUT_STARTED"]:
            state = 1
        if state_string == "OBS_WEBSOCKET_OUTPUT_PAUSED":
            state = 2

        print(state_string)

        self.show_for_state(state)

    def show_current_rec_status(self, new_paused = False):
        active = self.PLUGIN_BASE.obs.get_record_status().datain["outputActive"]
        paused = self.PLUGIN_BASE.obs.get_record_status().datain["outputPaused"]
        if active and not paused:
            self.show_for_state(1)
        elif paused:
            self.show_for_state(2)
        else:
            self.show_for_state(0)

    def show_for_state(self, state: int):
        """
        0: Not Recording
        1: Recording
        2: Paused
        3: Stopping in progress
        """
        image = "record_inactive.png"
        if state == 1:
            self.set_bottom_label("Pause", font_size=16)
            image = "record_pause.png"
        if state == 2:
            self.set_bottom_label("Resume", font_size=16)
            image = "record_resume.png"
        else:
            self.set_bottom_label(None)

        self.set_key(media_path=os.path.join(self.PLUGIN_BASE.PATH, "assets", image))

    def on_key_down(self):
        self.PLUGIN_BASE.obs.toggle_record_pause()


class OBS(PluginBase):
    def __init__(self):
        self.PLUGIN_NAME = "OBS"
        self.GITHUB_REPO = "https://github.com/your-github-repo"
        super().__init__()

        self.obs = OBSController()

        self.add_action(ToggleRecord)
        self.add_action(RecPlayPause)