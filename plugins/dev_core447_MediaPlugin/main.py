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

class Output(ActionBase):
    ACTION_NAME = "Pause"
    def __init__(self, deck_controller, page, coords):
        super().__init__(deck_controller=deck_controller, page=page, coords=coords)

        self.current_status = None
        self.show_current_media_status()
        
    def on_key_down(self):
        status = self.PLUGIN_BASE.mc.status(self.get_player_name())
        if status == "Playing":
            self.PLUGIN_BASE.mc.pause(self.get_player_name())
        else:
            self.PLUGIN_BASE.mc.play(self.get_player_name())

    def on_key_up(self):
        print("up")
        print(f"controller: {self.deck_controller}")\

    def on_tick(self):
        self.show_current_media_status()

    def get_custom_config_area(self) -> "Gtk.Widget":
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        button = Gtk.Button(label="Test")
        box.append(button)
        label = Gtk.Label(label="label")
        box.append(label)
        return box
    
    def get_config_rows(self) -> "list[Adw.PreferencesRow]":
        # Init ui elements
        self.player_model = Gtk.StringList()
        self.player_selector = Adw.ComboRow(model=self.player_model, title="Bind to player:", subtitle="Specify the player to controll")
        self.player_selector.set_enable_search(True) #TODO: Implement

        self.update_player_selector()
        self.player_selector.connect("notify::selected-item", self.on_change_player)

        self.label_toggle = Adw.SwitchRow(title="Show name of playing song", subtitle="Show the name of the currently playing song")
        self.label_toggle.connect("notify::active", self.on_toggle_label)

        # Load toggle state from settings
        settings = self.get_settings()
        if settings is not None:
            settings.setdefault("show_label", True)
            self.label_toggle.set_active(settings["show_label"])
        self.set_settings(settings)

        return [self.player_selector, self.label_toggle]

    ## Custom methods
    def on_change_player(self, combo, *args):
        settings = self.get_settings()
        if combo.get_selected_item().get_string() == "All Players":
            del settings["player_name"]
        else:
            settings["player_name"] = combo.get_selected_item().get_string()
        self.set_settings(settings)
    
    def update_player_selector(self):
        # Clear the model
        for i in range(self.player_model.get_n_items()):
            self.player_model.remove(0)

        players = self.PLUGIN_BASE.mc.get_player_names(remove_duplicates=True)

        self.player_model.append("All Players")

        for player in players:
            self.player_model.append(player)

        # Add from settings if not already in the model
        if self.get_player_name() is not None:
            if self.get_player_name() not in players:
                self.player_model.append(self.get_player_name())

        # Select from settings
        if self.get_player_name() is not None:
            position = 0
            for i in range(self.player_model.get_n_items()):
                item = self.player_model.get_item(i).get_string()
                n = self.get_player_name()
                print(f"item: {item}, n: {n}")
                if self.player_model.get_item(i).get_string() == self.get_player_name():
                    position = i
                    break
            self.player_selector.set_selected(position)
    
    def get_player_name(self):
        settings = self.get_settings()
        if settings is not None:
            return settings.get("player_name")

    def show_current_media_status(self):
        if self.get_settings() == None:
            # Page not yet fully loaded
            return
        status = self.PLUGIN_BASE.mc.status(self.get_player_name())

        file = {
            "Playing": os.path.join(self.PLUGIN_BASE.PATH, "assets", "pause.png"),
            "Paused": os.path.join(self.PLUGIN_BASE.PATH, "assets", "play.png"),
        }
        if isinstance(status, list):
            return
        
        title = self.PLUGIN_BASE.mc.title(self.get_player_name())
        label = None
        margins = [0, 0, 0, 0]
        if self.get_settings().setdefault("show_label", True):
            if isinstance(title, list):
                if len(title) > 0:
                    label = title[0]
                    margins = [5, 0, 5, 10]
            if isinstance(title, str):
                if len(title) > 0:
                    label = title
                    margins = [5, 0, 5, 10]
            self.set_bottom_label(self.shorten_title(label, 10), font_size=12)
        else:
            self.set_bottom_label(None)
        
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

        self.set_key(media_path = file[status], margins=margins)

    def shorten_title(self, title, length):
        if title is None:
            return
        if len(title) > length:
            return title[:length-2] + ".."
        return title
    
    def on_toggle_label(self, switch, *args):
        settings = self.get_settings()
        settings["show_label"] = switch.get_active()
        self.set_settings(settings)

class Test(PluginBase):
    PLUGIN_NAME = "MediaPlugin"
    GITHUB_REPO = "https://github.com/your-github-repo"
    def __init__(self):
        super().__init__()

        self.mc = MediaController()

        self.add_action(Output)