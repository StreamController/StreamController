from src.backend.PluginManager.ActionBase import ActionBase
from src.backend.PluginManager.PluginBase import PluginBase

# Import gtk modules
import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw

import sys
import os
from loguru import logger as log
from PIL import Image, ImageEnhance

# Add plugin to sys.paths
sys.path.append(os.path.dirname(__file__))

from MediaController import MediaController
from MediaAction import MediaAction

class PlayPause(MediaAction):
    ACTION_NAME = "Play/Pause"
    def __init__(self, deck_controller, page, coords):
        super().__init__(deck_controller=deck_controller, page=page, coords=coords)

        self.show_current_media_status()
        
    def on_key_down(self):
        status = self.PLUGIN_BASE.mc.status(self.get_player_name())
        if status == "Playing":
            self.PLUGIN_BASE.mc.pause(self.get_player_name())
        else:
            self.PLUGIN_BASE.mc.play(self.get_player_name())

    def on_key_up(self):
        pass

    def on_tick(self):
        self.show_current_media_status()

class Next(MediaAction):
    ACTION_NAME = "Next"
    def __init__(self, deck_controller, page, coords):
        super().__init__(deck_controller=deck_controller, page=page, coords=coords)

        self.margins = [5, 0, 5, 10] if self.show_title(reload_key=False) else [0, 0, 0, 0]
        
        self.set_key(margins=self.margins, media_path=os.path.join(self.PLUGIN_BASE.PATH, "assets", "next.png"))

    def on_key_down(self):
        self.PLUGIN_BASE.mc.next(self.get_player_name())

    def on_tick(self):
        new_margins = [5, 0, 5, 10] if self.show_title() else [0, 0, 0, 0]
        if self.margins != new_margins:
            self.margins = new_margins
            self.set_key(margins=self.margins, media_path=os.path.join(self.PLUGIN_BASE.PATH, "assets", "next.png"))

class Previous(MediaAction):
    ACTION_NAME = "Previous"
    def __init__(self, deck_controller, page, coords):
        super().__init__(deck_controller=deck_controller, page=page, coords=coords)

        self.margins = [5, 0, 5, 10] if self.show_title(reload_key = False) else [0, 0, 0, 0]
        
        self.set_key(margins=self.margins, media_path=os.path.join(self.PLUGIN_BASE.PATH, "assets", "previous.png"))

    def on_key_down(self):
        self.PLUGIN_BASE.mc.previous(self.get_player_name())

    def on_tick(self):
        new_margins = [5, 0, 5, 10] if self.show_title(reload_key=True) else [0, 0, 0, 0]
        if self.margins != new_margins:
            self.margins = new_margins
            self.set_key(margins=self.margins, media_path=os.path.join(self.PLUGIN_BASE.PATH, "assets", "previous.png"))

class MediaPlugin(PluginBase):
    PLUGIN_NAME = "MediaPlugin"
    GITHUB_REPO = "https://github.com/your-github-repo"
    def __init__(self):
        super().__init__()

        self.mc = MediaController()

        self.add_action(PlayPause)
        self.add_action(Next)
        self.add_action(Previous)