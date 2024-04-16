import Pyro5.api
import os
from typing import TYPE_CHECKING
import argparse
import sys

argparser = argparse.ArgumentParser()
argparser.add_argument("-b", help="Open in background", action="store_true")
argparser.add_argument("--devel", help="Developer mode", action="store_true")
argparser.add_argument("--close-running", help="Close running", action="store_true")
argparser.add_argument("--data", help="Data path", type=str)
argparser.add_argument("app_args", nargs="*")

DATA_PATH = os.path.join(os.path.expanduser("~"), ".var", "app", "com.core447.StreamController", "data") # Maybe use XDG_DATA_HOME instead
if argparser.parse_args().data:
    DATA_PATH = argparser.parse_args().data

# Add data path to sys.path
sys.path.append(DATA_PATH)

if TYPE_CHECKING:
    from src.app import App
    from locales.LocaleManager import LocaleManager
    from src.backend.AssetManagerBackend import AssetManagerBackend
    from src.windows.AssetManager.AssetManager import AssetManager
    from src.backend.MediaManager import MediaManager
    from src.backend.PageManagement.PageManagerBackend import PageManagerBackend
    from src.backend.SettingsManager import SettingsManager
    from src.backend.DeckManagement.DeckManager import DeckManager
    from src.backend.PluginManager.PluginManager import PluginManager
    from src.backend.IconPackManagement.IconPackManager import IconPackManager
    from src.backend.WallpaperPackManagement.WallpaperPackManager import WallpaperPackManager
    from src.windows.Store.StoreBackend import StoreBackend
    from src.Signals.SignalManager import SignalManager
    from src.backend.WindowGrabber.WindowGrabber import WindowGrabber
    from src.backend.GnomeExtensions import GnomeExtensions
    from src.windows.Store.Store import Store
    from src.backend.PermissionManagement.FlatpakPermissionManager import FlatpakPermissionManager


top_level_dir:str = os.path.dirname(__file__)
lm:"LocaleManager" = None
media_manager:"MediaManager" = None #MediaManager
asset_manager_backend:"AssetManagerBackend" = None #AssetManager
asset_manager: "AssetManager" = None
page_manager_backend:"PageManagerBackend" = None #PageManager
gnome_extensions:"GnomeExtensions" = None
settings_manager:"SettingsManager" = None #SettingsManager
app:"App" = None #App
deck_manager:"DeckManager" = None #DeckManager
plugin_manager:"PluginManager" = None #PluginManager
video_extensions = ["mp4", "mov", "MP4", "MOV", "mkv", "MKV", "webm", "WEBM", "gif", "GIF"]
image_extensions = ["png", "jpg", "jpeg"]
svg_extensions = ["svg", "SVG"]
icon_pack_manager: "IconPackManager" = None
wallpaper_pack_manager: "WallpaperPackManager" = None
store_backend: "StoreBackend" = None
pyro_daemon: Pyro5.api.Daemon = None
signal_manager: "SignalManager" = None
window_grabber: "WindowGrabber" = None
store: "Store" = None # Only if opened
flatpak_permission_manager: "FlatpakPermissionManager" = None
threads_running: bool = True


app_version: str = "1.4.11-beta" # In breaking.feature.fix-state format
exact_app_version_check: bool = False
logs: list[str] = []

release_notes: str = "<ul> \
    <li>Bugfixes</li> \
    <li>Svg support</li> \
    </ul>"