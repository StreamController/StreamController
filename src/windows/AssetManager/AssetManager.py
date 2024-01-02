"""
Author: Core447
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

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, GLib, Gio, Gdk, GObject, GdkPixbuf

# Import Python modules
from loguru import logger as log
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from src.windows.mainWindow.mainWindow import MainWindow

# Import globals
import globals as gl

# Import own modules
from src.windows.AssetManager.InfoPage import InfoPage
from src.windows.AssetManager.CustomAssets.Chooser import CustomAssetChooser
from src.windows.AssetManager.IconPacks.Stack import IconPackChooserStack


class AssetManager(Gtk.ApplicationWindow):
    def __init__(self, main_window: "MainWindow", *args, **kwargs):
        super().__init__(
            title="Asset Manager",
            default_width=1050,
            default_height=750,
            transient_for=main_window,
            *args, **kwargs
            )
        self.main_window = main_window

        # Callback func
        self.callback_func = None
        self.callback_args = []
        self.callback_kwargs = {}

        self.build()

    def build(self):
        self.main_stack = Gtk.Stack(transition_duration=200, transition_type=Gtk.StackTransitionType.SLIDE_LEFT_RIGHT, hexpand=True, vexpand=True)
        self.set_child(self.main_stack)
        self.asset_chooser = AssetChooser(self)
        self.main_stack.add_titled(self.asset_chooser, "Asset Chooser", "Asset Chooser")

        self.asset_info = InfoPage(self)
        self.main_stack.add_titled(self.asset_info, "Asset Info", "Asset Info")

        # Header bar
        self.header_bar = Gtk.HeaderBar()
        self.set_titlebar(self.header_bar)

        self.stack_switcher = Gtk.StackSwitcher(stack=self.asset_chooser)
        self.header_bar.set_title_widget(self.stack_switcher)

        self.back_button = Gtk.Button(icon_name="go-previous", visible=False)
        self.back_button.connect("clicked", self.on_back_button_click)
        self.header_bar.pack_start(self.back_button)

    def show_for_path(self, path, callback_func=None, *callback_args, **callback_kwargs):
        self.callback_func = callback_func
        self.callback_args = callback_args
        self.callback_kwargs = callback_kwargs
        
        self.asset_chooser.show_for_path(path, callback_func, *callback_args, **callback_kwargs)
        self.main_stack.set_visible_child(self.asset_chooser)
        self.back_button.set_visible(False)
        self.present()

    def show_info_for_asset(self, asset:dict):
        self.asset_info.show_for_asset(asset)
        self.main_stack.set_visible_child(self.asset_info)
        self.back_button.set_visible(True)
        self.present()

    def show_info(self, internal_path:str = None , licence_name: str = None, license_url: str = None, author: str = None, license_comment: str = None):
        self.asset_info.show_info(internal_path, licence_name, license_url, author, license_comment)

        self.main_stack.set_visible_child(self.asset_info)
        self.back_button.set_visible(True)
        self.present()

    def on_back_button_click(self, button):
        self.main_stack.set_visible_child(self.asset_chooser)
        self.back_button.set_visible(False)


class AssetChooser(Gtk.Stack):
    def __init__(self, asset_manager: AssetManager, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.asset_manager = asset_manager

        self.build()

    def build(self):
        self.custom_asset_chooser = CustomAssetChooser(self.asset_manager)
        self.add_titled(self.custom_asset_chooser, "custom-assets", "Custom Assets")

        self.icon_pack_chooser = IconPackChooserStack(self.asset_manager)
        self.add_titled(self.icon_pack_chooser, "icon-packs", "Icon Packs")

    def show_for_path(self, *args, **kwargs):
        self.custom_asset_chooser.show_for_path(*args, **kwargs)