from src.backend.PluginManager.ActionBase import ActionBase

# Import gtk modules
import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw

from PIL import Image, ImageEnhance
import os

class MediaAction(ActionBase):
    def __init__(self, deck_controller, page, coords):
        super().__init__(deck_controller=deck_controller, page=page, coords=coords)

        self.current_status = None
        
    def on_key_down(self):
        pass

    def on_key_up(self):
        pass

    def on_tick(self):
        pass
    
    def get_config_rows(self) -> "list[Adw.PreferencesRow]":
        # Init ui elements
        self.player_model = Gtk.StringList()
        self.player_selector = Adw.ComboRow(model=self.player_model, title="Bind to player:", subtitle="Specify the player to controll")
        self.player_selector.set_enable_search(True) #TODO: Implement


        self.label_toggle = Adw.SwitchRow(title="Show name of playing song", subtitle="Show the name of the currently playing song")

        self.load_config_defaults()

        self.player_selector.connect("notify::selected-item", self.on_change_player)
        self.label_toggle.connect("notify::active", self.on_toggle_label)

        return [self.player_selector, self.label_toggle]

    ## Custom methods
    def load_config_defaults(self):
        settings = self.get_settings()
        if settings == None:
            return
        
        show_label = settings.setdefault("show_label", True)

        # Update ui
        self.label_toggle.set_active(show_label)
        self.update_player_selector()
    
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
    
    def on_change_player(self, combo, *args):
        settings = self.get_settings()
        if combo.get_selected_item().get_string() == "All Players":
            del settings["player_name"]
        else:
            settings["player_name"] = combo.get_selected_item().get_string()
        self.set_settings(settings)

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

        self.set_key(media_path = file[status], margins=margins)

    def show_title(self, reload_key = True) -> bool:
        if self.get_settings() == None:
            return
        if self.get_settings().setdefault("show_label", True):
            title = self.PLUGIN_BASE.mc.title(self.get_player_name())
            label = None
            if isinstance(title, list):
                if len(title) > 0:
                    label = title[0]
                    # margins = [5, 0, 5, 10]
            if isinstance(title, str):
                if len(title) > 0:
                    label = title
                    # margins = [5, 0, 5, 10]
            self.set_bottom_label(self.shorten_label(label, 10), font_size=12, reload=reload_key)
            return True
        else:
            self.set_bottom_label(None, reload=reload_key)
            return False

    

    def shorten_label(self, label, length):
        if label is None:
            return
        if len(label) > length:
            return label[:length-2] + ".."
        return label
    
    def on_toggle_label(self, switch, *args):
        settings = self.get_settings()
        settings["show_label"] = switch.get_active()
        self.set_settings(settings)