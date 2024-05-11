from gi.repository import Gtk, Adw

from typing import TYPE_CHECKING

from src.windows.mainWindow.elements.Sidebar.elements.ActionManager import ActionManager
from src.windows.mainWindow.DeckPlus.ScreenBar import ScreenBarImage

from PIL import Image

if TYPE_CHECKING:
    from src.windows.mainWindow.elements.Sidebar.Sidebar import Sidebar

import globals as gl

class ScreenEditor(Gtk.ScrolledWindow):
    def __init__(self, sidebar: "Sidebar"):
        self.sidebar = sidebar
        super().__init__(hexpand=True, vexpand=True)

        self.build()

    def build(self):
        self.clamp = Adw.Clamp(hexpand=True, vexpand=True)
        self.set_child(self.clamp)

        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, hexpand=True)
        self.clamp.set_child(self.main_box)

        self.header = Gtk.Label(label="Touch Bar", css_classes=["large-title", "bold"], margin_top=15, margin_bottom=30)
        self.main_box.append(self.header)

        self.swipe_left_group = Adw.PreferencesGroup(title="Swipe Left")
        self.main_box.append(self.swipe_left_group)

        self.swipe_right_group = Adw.PreferencesGroup(title="Swipe Right", margin_top=10)
        self.main_box.append(self.swipe_right_group)

        self.swipe_left_configurator = ActionManager(self.sidebar)
        self.swipe_left_group.add(self.swipe_left_configurator)

        self.swipe_right_configurator = ActionManager(self.sidebar)
        self.swipe_right_group.add(self.swipe_right_configurator)

    def load(self, state):
        self.swipe_left_configurator.load_for_screen("swipe-left", state)
        self.swipe_right_configurator.load_for_screen("swipe-right", state)