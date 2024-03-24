"""
Year: 2023

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
any later version.

This programm comes with ABSOLUTELY NO WARRANTY!

You should have received a copy of the GNU General Public License
along with this program. If not, see <https://www.gnu.org/licenses/>.
"""
# Import gtk modules
import gi

from src.backend.DeckManagement.HelperMethods import is_video


gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, GLib, Gio, Gdk, GObject, GdkPixbuf

# Import Python modules
from loguru import logger as log
from fuzzywuzzy import fuzz
import webbrowser as web
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from src.windows.mainWindow.mainWindow import MainWindow

# Import globals
import globals as gl

# Import own modules
from src.backend.DeckManagement.ImageHelpers import image2pixbuf
from src.windows.Store.Plugins.PluginPage import PluginPage
from src.windows.Store.Icons.IconPage import IconPage
from src.windows.Store.StorePage import StorePage
from src.windows.Store.Wallpapers.WallpaperPage import WallpaperPage

class Store(Gtk.ApplicationWindow):
    def __init__(self, main_window: "MainWindow", *args, **kwargs):
        super().__init__(
            title="Store",
            default_width=1050,
            default_height=750,
            transient_for=main_window,
            *args, **kwargs
            )
        self.main_window = main_window

        self.backend = gl.store_backend

        self.currently_downloading: bool = False # Used to prevent multiple downloads because this may lead to errors during plugin initialization

        self.build()

    def build(self):
        # Header bar
        self.header = Gtk.HeaderBar(css_classes=["flat"])
        self.set_titlebar(self.header)

        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.set_child(self.main_box)

        self.main_stack = Gtk.Stack(transition_type=Gtk.StackTransitionType.SLIDE_LEFT_RIGHT, hexpand=True, vexpand=True)
        self.main_box.append(self.main_stack)

        # Header stack switcher
        self.stack_switcher = Gtk.StackSwitcher(stack=self.main_stack)
        self.header.set_title_widget(self.stack_switcher)

        # Header back button
        self.back_button = Gtk.Button(icon_name="go-previous", visible=False)
        self.back_button.connect("clicked", self.on_back_button_click)
        self.header.pack_start(self.back_button)

        self.plugin_page = PluginPage(store=self)
        self.icon_page = IconPage(store=self)
        self.wallpaper_page = WallpaperPage(store=self)

        self.main_stack.add_titled(self.plugin_page, "Plugins", gl.lm.get("store.plugins.section"))
        self.main_stack.add_titled(self.icon_page, "Icons", gl.lm.get("store.icons.section"))
        self.main_stack.add_titled(self.wallpaper_page, "Wallpapers", gl.lm.get("store.wallpapers.section"))

    def on_back_button_click(self, button: Gtk.Button):
        # Switch active page back from info page
        self.main_stack.get_visible_child().set_info_visible(False)