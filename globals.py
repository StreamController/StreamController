import argparse
import json
import os
import sys
from typing import TYPE_CHECKING

import Pyro5.api
from loguru import logger as log

from src.backend.DeckManagement.HelperMethods import find_fallback_font

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
    from src.backend.Store.StoreBackend import StoreBackend
    from src.Signals.SignalManager import SignalManager
    from src.backend.WindowGrabber.WindowGrabber import WindowGrabber
    from src.backend.GnomeExtensions import GnomeExtensions
    from src.windows.Store.Store import Store
    from src.backend.PermissionManagement.FlatpakPermissionManager import FlatpakPermissionManager
    from src.windows.PageManager.PageManager import PageManager
    from src.tray import TrayIcon
    from src.backend.Logger import Logger

# ─────────────────────────────────────────────────────────────
# ARGUMENT PARSING
# ─────────────────────────────────────────────────────────────
argparser = argparse.ArgumentParser()

## Static Values
argparser.add_argument("-b", help="Open in background", action="store_true")
argparser.add_argument("--devel", help="Developer mode (disables auto update)", action="store_true")
argparser.add_argument("--skip-load-hardware-decks", help="Skips initilization/use of hardware decks", action="store_true")
argparser.add_argument("--close-running", help="Close running", action="store_true")
argparser.add_argument("--data", help="Data path", type=str)
argparser.add_argument("app_args", nargs="*")

## Api Calls
argparser.add_argument("--change-page", action="append", nargs=2, help="Change the page for a device", metavar=("SERIAL_NUMBER", "PAGE_NAME"))

# ─────────────────────────────────────────────────────────────
# PATHS AND STATIC CONFIGURATION
# ─────────────────────────────────────────────────────────────
MAIN_PATH: str
VAR_APP_PATH = os.path.join(os.path.expanduser("~"), ".var", "app", "com.core447.StreamController")
STATIC_SETTINGS_FILE_PATH = os.path.join(VAR_APP_PATH, "static", "settings.json")
DATA_PATH = os.path.join(VAR_APP_PATH, "data") # Maybe use XDG_DATA_HOME instead
PLUGIN_DIR = os.path.join(DATA_PATH, "plugins")
TOP_LEVEL_DIR: str = os.path.dirname(__file__)

args = argparser.parse_args()

if args.data:
    DATA_PATH = args.data
elif not args.devel:
    # Check static settings
    if os.path.exists(STATIC_SETTINGS_FILE_PATH):
        try:
            with open(STATIC_SETTINGS_FILE_PATH) as f:
                settings = json.load(f)
                if "data-path" in settings:
                    DATA_PATH = settings["data-path"]
            log.info(f"Using data path from static settings: {DATA_PATH}")
        except Exception as e:
            log.error(f"Failed to set data path from static settings: {e}")

if not os.path.exists(DATA_PATH):
    log.info(f"Creating data path: {DATA_PATH}")
    try:
        os.makedirs(DATA_PATH)
    except Exception as e:
        log.error(f"Failed to create data path: {e}\nPlease change the data path manually in the config file under {STATIC_SETTINGS_FILE_PATH}")
        sys.exit(1)

# Used for nix packaging
if os.getenv("PLUGIN_DIR") is not None:
    PLUGIN_DIR = os.getenv("PLUGIN_DIR")
    top_level_folder = os.path.dirname(PLUGIN_DIR)
    sys.path.append(top_level_folder)

    if os.path.exists(os.path.join(DATA_PATH, "plugins")):
        log.warning(f"You're using a plugin dir path outside of your data dir, but also have a plugin dir in the data dir. This may cause problems.")

os.makedirs(PLUGIN_DIR, exist_ok=True)

# Add data path to sys.path
sys.path.append(DATA_PATH)

# ─────────────────────────────────────────────────────────────
# GLOBAL SINGLETONS (WILL BE SET LATER)
# ─────────────────────────────────────────────────────────────

# Singleton added
app:"App" = None #App
lm:"LocaleManager" = None

# No singleton
media_manager:"MediaManager" = None #MediaManager  # Rework to use Static methods
asset_manager_backend:"AssetManagerBackend" = None #AssetManager
asset_manager: "AssetManager" = None
page_manager_window: "PageManager" = None # Only if opened
page_manager:"PageManagerBackend" = None #PageManager #TODO: Rename to page_manager_backend in 2.0.0
gnome_extensions:"GnomeExtensions" = None
settings_manager:"SettingsManager" = None #SettingsManager
deck_manager:"DeckManager" = None #DeckManager
plugin_manager:"PluginManager" = None #PluginManager
icon_pack_manager: "IconPackManager" = None
wallpaper_pack_manager: "WallpaperPackManager" = None
store_backend: "StoreBackend" = None
pyro_daemon: Pyro5.api.Daemon = None
signal_manager: "SignalManager" = None
window_grabber: "WindowGrabber" = None
lock_screen_detector: "LockScreenDetector" = None
store: "Store" = None # Only if opened
flatpak_permission_manager: "FlatpakPermissionManager" = None
tray_icon: "TrayIcon" = None

# ─────────────────────────────────────────────────────────────
# GLOBAL STATE VARIABLES
# ─────────────────────────────────────────────────────────────
VIDEO_EXTENSIONS = ["mp4", "mov", "MP4", "MOV", "mkv", "MKV", "webm", "WEBM", "gif", "GIF"]
IMAGE_EXTENSIONS = ["png", "jpg", "jpeg"]
SVG_EXTENSIONS = ["svg", "SVG"]
FALLBACK_FONT: str = find_fallback_font()
APP_VERSION: str = "1.5.0-beta.10"  # In breaking.feature.fix-state format

threads_running: bool = True
app_loading_finished_tasks: callable = []
api_page_requests: dict[str, str] = {} # Stores api page requests made my --change-page
showed_donate_window: bool = False
screen_locked: bool = False
loggers: dict[str, "Logger"] = {}
exact_app_version_check: bool = False
logs: list[str] = []

# ─────────────────────────────────────────────────────────────
# RELEASE NOTES LOADING
# ─────────────────────────────────────────────────────────────
RELEASE_NOTES: str

with open(os.path.join(TOP_LEVEL_DIR, "Assets", "RELEASE_NOTES"), "r") as f:
    RELEASE_NOTES = f.read()
