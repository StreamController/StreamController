from src.backend.PluginManager.ActionBase import ActionBase
from src.backend.PluginManager.PluginBase import PluginBase

# Import gtk modules
import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw

import sys
import os
from PIL import Image
from loguru import logger as log

# Add plugin to sys.paths
sys.path.append(os.path.dirname(__file__))

# Import globals
import globals as gl

class ChangePage(ActionBase):
    ACTION_NAME = "Change Page"
    def __init__(self, deck_controller, page, coords):
        super().__init__(deck_controller=deck_controller, page=page, coords=coords)

        self.set_default_image(Image.open(os.path.join(self.PLUGIN_BASE.PATH, "assets", "folder.png")))

    def on_ready(self):
        # Ensures that there is always one page selected
        settings = self.get_settings()
        settings.setdefault("selected_page", gl.page_manager.get_pages()[0])
        self.set_settings(settings)

    def get_config_rows(self) -> list:
        self.page_model = Gtk.StringList()
        self.page_selector = Adw.ComboRow(model=self.page_model, title="Page:",
                                          subtitle="Select page to swtich to")
        
        self.load_page_model()

        
        self.load_config_defaults()

        self.page_selector.connect("notify::selected-item", self.on_change_page)

        return [self.page_selector]
        

    def load_page_model(self):
        # Clear
        for i in range(self.page_model.get_n_items()):
            self.page_model.remove(0)

        # Add pages
        for page in gl.page_manager.get_pages(remove_extension=True):
            self.page_model.append(page)

    def load_config_defaults(self):
        settings = self.get_settings()
        if settings == None:
            return
        
        # Update page selector
        selected_page = settings.setdefault("selected_page", None)
        position = 0
        if selected_page is not None:
            for i in range(self.page_model.get_n_items()):
                if self.page_model.get_item(i).get_string() == selected_page:
                    position = i
                    break
        self.page_selector.set_selected(position)

    def on_change_page(self, combo, *args):
        settings = self.get_settings()
        settings["selected_page"] = combo.get_selected_item().get_string()
        self.set_settings(settings)

    def on_key_down(self):
        page = gl.page_manager.create_page_for_name(self.get_settings()["selected_page"], deck_controller = self.deck_controller)
        self.deck_controller.load_page(page)


class DeckPlugin(PluginBase):
    def __init__(self):
        self.PLUGIN_NAME = "Deck"
        self.GITHUB_REPO = "https://github.com/your-github-repo"
        super().__init__()

        self.add_action(ChangePage)