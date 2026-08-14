import json
import Pyro5.api
import os
from collections import deque
from typing import TYPE_CHECKING
import sys
from loguru import logger as log

from src.CLI import build_argparser
from src.backend.DeckManagement.HelperMethods import find_fallback_font

# Automatically detect macOS
IS_MAC = sys.platform == "darwin"

argparser = build_argparser()

MAIN_PATH: str
VAR_APP_PATH = os.path.join(os.path.expanduser("~"), ".var", "app", "com.core447.StreamController")
STATIC_SETTINGS_FILE_PATH = os.path.join(VAR_APP_PATH, "static", "settings.json")

DATA_PATH = os.path.join(VAR_APP_PATH, "data") # Maybe use XDG_DATA_HOME instead
if argparser.parse_args().data:
    DATA_PATH = argparser.parse_args().data
elif not argparser.parse_args().devel:
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

PLUGIN_DIR = os.path.join(DATA_PATH, "plugins")
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
    from src.backend.SDPlusBarWallpaperPackManagement.SDPlusBarWallpaperPackManager import SDPlusBarWallpaperPackManager
    from src.backend.Store.StoreBackend import StoreBackend
    from src.Signals.SignalManager import SignalManager
    from src.backend.WindowGrabber.WindowGrabber import WindowGrabber
    from src.backend.GnomeExtensions import GnomeExtensions
    from src.windows.Store.Store import Store
    from src.backend.PermissionManagement.FlatpakPermissionManager import FlatpakPermissionManager
    from src.windows.PageManager.PageManager import PageManager
    from src.backend.LockScreenManager.LockScreenManager import LockScreenManager
    from src.tray import TrayIcon
    from src.backend.Logger import Logger


top_level_dir:str = os.path.dirname(__file__)
lm:"LocaleManager" = None
media_manager:"MediaManager" = None #MediaManager
asset_manager_backend:"AssetManagerBackend" = None #AssetManager
asset_manager: "AssetManager" = None
page_manager_window: "PageManager" = None # Only if opened
page_manager:"PageManagerBackend" = None #PageManager #TODO: Rename to page_manager_backend in 2.0.0
gnome_extensions:"GnomeExtensions" = None
settings_manager:"SettingsManager" = None #SettingsManager
ai_manager:"AIManager" = None #AIManager
action_doc_registry:"ActionDocRegistry" = None #ActionDocRegistry
app:"App" = None #App
deck_manager:"DeckManager" = None #DeckManager
plugin_manager:"PluginManager" = None #PluginManager
video_extensions = ["mp4", "mov", "MP4", "MOV", "mkv", "MKV", "webm", "WEBM", "gif", "GIF"]
image_extensions = ["png", "jpg", "jpeg"]
svg_extensions = ["svg", "SVG"]
icon_pack_manager: "IconPackManager" = None
wallpaper_pack_manager: "WallpaperPackManager" = None
sd_plus_bar_wallpaper_pack_manager: "SDPlusBarWallpaperPackManager" = None
store_backend: "StoreBackend" = None
pyro_daemon: Pyro5.api.Daemon = None
signal_manager: "SignalManager" = None
window_grabber: "WindowGrabber" = None
lock_screen_detector: "LockScreenManager" = None
store: "Store" = None # Only if opened
flatpak_permission_manager: "FlatpakPermissionManager" = None
threads_running: bool = True
app_loading_finished_tasks: callable = []
api_page_requests: dict[str, str] = {} # Stores api page requests made my --change-page
api_state_requests: dict[str, dict] = {} # Stores api state change requests made by --change-state
api_action_requests: dict[str, dict] = {} # Stores api action trigger requests made by --action
tray_icon: "TrayIcon" = None
fallback_font: str = find_fallback_font()
showed_donate_window: bool = False
screen_locked: bool = False
loggers: dict[str, "Logger"] = {}

app_version: str = "1.5.0-beta.16"  # In breaking.feature.fix-state format
logs = deque(maxlen=5000)

release_notes: str = """
<p>Features:</p>
    <ul>
        <li>Sticky actions: keep actions on the same key across all pages</li>
        <li>Full support for the Stream Deck Neo</li>
        <li>New icon chooser in the asset manager</li>
        <li>Create your own asset packs</li>
        <li>Download premade pages from the store</li>
        <li>Optional AI assistant to help configure actions (off by default)</li>
        <li>Choose a plugin's git branch when installing from the store</li>
        <li>Use multiple wallpapers</li>
        <li>Rename decks</li>
        <li>Search entry in the page selector</li>
        <li>Option to keep states between restarts</li>
        <li>Option to not shrink the background on key press</li>
        <li>Choose the deck type of fake decks</li>
        <li>Daemon-only mode for running without the window</li>
        <li>Restart option in the tray menu</li>
        <li>Greatly extended command line interface</li>
    </ul>
<p>Improvements:</p>
    <ul>
        <li>Lower CPU and RAM usage, faster page switching and faster resume from suspend</li>
        <li>Reorder actions via drag and drop</li>
        <li>Page import and export now include the used assets and plugins</li>
        <li>More responsive Stream Deck+ touchscreen</li>
        <li>Decks automatically reconnect after temporary USB errors</li>
        <li>Sensitive information is redacted from log files</li>
        <li>Settings and pages are saved atomically, so a crash can no longer corrupt them</li>
        <li>Reset buttons of spinners no longer react to accidental clicks</li>
        <li>StreamController now tells you when an input is controlled by a stick action</li>
        <li>Default regex for automatic page switching</li>
    </ul>
<p>Fixes:</p>
    <ul>
        <li>Deck frozen after unlocking the screen</li>
        <li>Random crashes caused by background threads</li>
        <li>Plugin backends breaking after a Python update</li>
        <li>Proper GIF support with transparency and per-frame timing</li>
        <li>App silently quitting while running in the background</li>
        <li>Page switch could leave a key in the pressed state</li>
        <li>Various problems with rotated decks</li>
        <li>Screen bar problems on the Stream Deck Plus XL</li>
        <li>Sidebar not fully updating when switching pages</li>
        <li>Tray icon sometimes not loading correctly</li>
        <li>Infinite loading in the asset manager when adding invalid assets</li>
        <li>Wrong icon sizes in the onboarding dialog</li>
        <li>Open button in the data path settings</li>
        <li>Automatic page switching on Niri</li>
    </ul>
"""
