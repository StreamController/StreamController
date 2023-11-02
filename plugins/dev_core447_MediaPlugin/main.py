from src.backend.PluginManager.ActionBase import ActionBase
from src.backend.PluginManager.PluginBase import PluginBase

# Import gtk modules
import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw

class Output(ActionBase):
    ACTION_NAME = "Pause"
    def __init__(self, deck_controller, page, coords):
        super().__init__(deck_controller=deck_controller, page=page, coords=coords)

    def on_key_down(self):
        print("down")
        print(f"controller: {self.deck_controller}")

    def on_key_up(self):
        print("up")
        print(f"controller: {self.deck_controller}")

    def get_custom_config_area(self) -> "Gtk.Widget":
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        button = Gtk.Button(label="Test")
        box.append(button)
        label = Gtk.Label(label="label")
        box.append(label)
        return box
    
    def get_config_rows(self) -> "list[Adw.PreferencesRow]":
        # row = Adw.SwitchRow()
        row = Adw.PreferencesRow()
        row.set_child(Gtk.Box(margin_bottom=100))
        return [row]

class Test(PluginBase):
    PLUGIN_NAME = "MediaPlugin"
    GITHUB_REPO = "https://github.com/your-github-repo"
    def __init__(self):
        super().__init__()

        self.add_action(Output)