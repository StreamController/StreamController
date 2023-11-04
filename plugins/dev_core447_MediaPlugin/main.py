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
import math

# Add plugin to sys.paths
sys.path.append(os.path.dirname(__file__))

from MediaController import MediaController
from MediaAction import MediaAction

class PlayPause(MediaAction):
    ACTION_NAME = "Play/Pause"
    def __init__(self, deck_controller, page, coords):
        super().__init__(deck_controller=deck_controller, page=page, coords=coords)

        self.update_image()
        
    def on_key_down(self):
        status = self.PLUGIN_BASE.mc.status(self.get_player_name())
        if status == "Playing":
            self.PLUGIN_BASE.mc.pause(self.get_player_name())
        else:
            self.PLUGIN_BASE.mc.play(self.get_player_name())

    def on_key_up(self):
        pass

    def on_tick(self):
        self.update_image()

    def update_image(self):
        if self.get_settings() == None:
            # Page not yet fully loaded
            return
        status = self.PLUGIN_BASE.mc.status(self.get_player_name())[0]

        file = {
            "Playing": os.path.join(self.PLUGIN_BASE.PATH, "assets", "pause.png"),
            "Paused": os.path.join(self.PLUGIN_BASE.PATH, "assets", "play.png"),
        }
        if isinstance(status, list):
            return
        
        margins = [10, 0, 0, 10] if self.show_title() else [0, 0, 0, 0]  
        
        if status == None:
            if self.current_status == None:
                self.current_status = "Playing"
            file_path = file[self.current_status]
            image = Image.open(file_path)
            enhancer = ImageEnhance.Brightness(image)
            image = enhancer.enhance(0.25)
            self.set_key(image=image, margins=margins)
            return

        self.current_status = status

        ## Thumbnail
        thumbnail = None
        if self.get_settings().setdefault("show_thumbnail", True):
            thumbnail = self.PLUGIN_BASE.mc.thumbnail(self.get_player_name())
            if thumbnail == None:
                thumbnail = Image.new("RGBA", (256, 256), (255, 255, 255, 0))
            elif isinstance(thumbnail, list):
                thumbnail = Image.open(thumbnail[0])

        image = Image.open(file[status])
        
        image = self.generate_image(background=thumbnail, icon=image, icon_margins=margins)

        self.set_key(image=image)

class Next(MediaAction):
    ACTION_NAME = "Next"
    def __init__(self, deck_controller, page, coords):
        super().__init__(deck_controller=deck_controller, page=page, coords=coords)

    def on_ready(self):
        self.update_image()

    def on_key_down(self):
        self.PLUGIN_BASE.mc.next(self.get_player_name())

    def on_tick(self):
        self.update_image()

    def update_image(self):
        has_title = self.show_title()
        new_margins = [10, 0, 0, 10] if has_title else [0, 0, 0, 0]

        image = Image.open(os.path.join(self.PLUGIN_BASE.PATH, "assets", "next.png"))
        
        thumbnail = None
        if self.get_settings().setdefault("show_thumbnail", True):
            thumbnail = self.PLUGIN_BASE.mc.thumbnail(self.get_player_name())
            if thumbnail == None:
                thumbnail = Image.new("RGBA", (256, 256), (255, 255, 255, 0))
            elif isinstance(thumbnail, list):
                thumbnail = Image.open(thumbnail[0])

        image = self.generate_image(background=thumbnail, icon=image, icon_margins=new_margins)

        self.set_key(image=image)     

class Previous(MediaAction):
    ACTION_NAME = "Previous"
    def __init__(self, deck_controller, page, coords):
        super().__init__(deck_controller=deck_controller, page=page, coords=coords)

    def on_ready(self):
        self.update_image()

    def on_key_down(self):
        self.PLUGIN_BASE.mc.previous(self.get_player_name())

    def on_tick(self):
        self.update_image()

    def update_image(self):
        has_title = self.show_title()
        new_margins = [10, 0, 5, 10] if has_title else [0, 0, 0, 0]

        image = Image.open(os.path.join(self.PLUGIN_BASE.PATH, "assets", "previous.png"))
        
        thumbnail = None
        if self.get_settings().setdefault("show_thumbnail", True):
            thumbnail = self.PLUGIN_BASE.mc.thumbnail(self.get_player_name())
            if thumbnail == None:
                thumbnail = Image.new("RGBA", (256, 256), (255, 255, 255, 0))
            elif isinstance(thumbnail, list):
                thumbnail = Image.open(thumbnail[0])

        image = self.generate_image(background=thumbnail, icon=image, icon_margins=new_margins)

        self.set_key(image=image)     

class MediaPlugin(PluginBase):
    PLUGIN_NAME = "MediaPlugin"
    GITHUB_REPO = "https://github.com/your-github-repo"
    def __init__(self):
        super().__init__()

        self.mc = MediaController()

        self.add_action(PlayPause)
        self.add_action(Next)
        self.add_action(Previous)