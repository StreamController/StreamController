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
        if status is None:
            return
        status = status[0]
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
        status = self.PLUGIN_BASE.mc.status(self.get_player_name())
        if isinstance(status, list):
            status = status[0]

        file = {
            "Playing": os.path.join(self.PLUGIN_BASE.PATH, "assets", "pause.png"),
            "Paused": os.path.join(self.PLUGIN_BASE.PATH, "assets", "play.png"),
        }
        if isinstance(status, list):
            return
        
        margins = [5, 0, 5, 10] if self.show_title() else [0, 0, 0, 0]  
        
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
                if thumbnail[0] == None:
                    return
                if not os.path.exists(thumbnail[0]):
                    return
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
        new_margins = [5, 0, 5, 10] if has_title else [0, 0, 0, 0]

        image = Image.open(os.path.join(self.PLUGIN_BASE.PATH, "assets", "next.png"))
        
        thumbnail = None
        if self.get_settings() is None:
            return
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
        new_margins = [5, 0, 5, 10] if has_title else [0, 0, 0, 0]

        image = Image.open(os.path.join(self.PLUGIN_BASE.PATH, "assets", "previous.png"))
        
        thumbnail = None
        if self.get_settings() is None:
            return
        if self.get_settings().setdefault("show_thumbnail", True):
            thumbnail = self.PLUGIN_BASE.mc.thumbnail(self.get_player_name())
            if thumbnail == None:
                thumbnail = Image.new("RGBA", (256, 256), (255, 255, 255, 0))
            elif isinstance(thumbnail, list):
                thumbnail = Image.open(thumbnail[0])

        image = self.generate_image(background=thumbnail, icon=image, icon_margins=new_margins)

        self.set_key(image=image) 

class Info(MediaAction):
    ACTION_NAME = "Info"
    def __init__(self, deck_controller, page, coords):
        super().__init__(deck_controller=deck_controller, page=page, coords=coords)

    def on_tick(self):
        self.update_image()

    def update_image(self):
        title = self.PLUGIN_BASE.mc.title(self.get_player_name())
        artist = self.PLUGIN_BASE.mc.artist(self.get_player_name())

        if title is not None:
            title = self.shorten_label(title[0], 10)
        if title is not None:
            artist = self.shorten_label(artist[0], 10)

        if self.get_settings() is None:
            return

        self.set_top_label(title, font_size=12)
        self.set_center_label(self.get_settings().get("seperator_text", "--"), font_size=12)
        self.set_bottom_label(artist, font_size=12)

        thumbnail = None
        if self.get_settings().setdefault("show_thumbnail", True):
            thumbnail = self.PLUGIN_BASE.mc.thumbnail(self.get_player_name())
            if thumbnail == None:
                thumbnail = Image.new("RGBA", (256, 256), (255, 255, 255, 0))
            elif isinstance(thumbnail, list):
                if thumbnail[0] == None:
                    return
                if not os.path.exists(thumbnail[0]):
                    return
                thumbnail = Image.open(thumbnail[0])
        self.set_key(image=thumbnail)

    def get_config_rows(self):
        super_rows =  super().get_config_rows()
        super_rows.pop(1) # Remove label toggle row
        self.seperator_text_entry = Adw.EntryRow(title="Seperator Text:")

        self.load_own_config_defaults()

        self.seperator_text_entry.connect("notify::text", self.on_change_seperator_text)

        return super_rows + [self.seperator_text_entry]
    
    def load_own_config_defaults(self):
        settings = self.get_settings()
        settings.setdefault("seperator_text", "--")
        self.set_settings(settings)

        # Update ui
        self.seperator_text_entry.set_text(settings["seperator_text"])

    def on_change_seperator_text(self, entry, *args):
        settings = self.get_settings()
        settings["seperator_text"] = entry.get_text()
        self.set_settings(settings)

        # Update image
        self.set_center_label(self.get_settings().get("seperator_text", "--"), font_size=12)

class MediaPlugin(PluginBase):
    def __init__(self):
        self.PLUGIN_NAME = "MediaPlugin"
        self.GITHUB_REPO = "https://github.com/your-github-repo"
        super().__init__()

        self.mc = MediaController()

        self.add_action(PlayPause)
        self.add_action(Next)
        self.add_action(Previous)
        self.add_action(Info)