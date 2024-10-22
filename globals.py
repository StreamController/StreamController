import json
import Pyro5.api
import os
from typing import TYPE_CHECKING
import argparse
import sys
from loguru import logger as log

from src.backend.DeckManagement.HelperMethods import find_fallback_font

argparser = argparse.ArgumentParser()
argparser.add_argument("-b", help="Open in background", action="store_true")
argparser.add_argument("--devel", help="Developer mode (disables auto update)", action="store_true")
argparser.add_argument("--skip-load-hardware-decks", help="Skips initilization/use of hardware decks", action="store_true")
argparser.add_argument("--close-running", help="Close running", action="store_true")
argparser.add_argument("--data", help="Data path", type=str)
argparser.add_argument("--change-page", action="append", nargs=2, help="Change the page for a device", metavar=("SERIAL_NUMBER", "PAGE_NAME"))
argparser.add_argument("app_args", nargs="*")

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
    from src.backend.Store.StoreBackend import StoreBackend
    from src.Signals.SignalManager import SignalManager
    from src.backend.WindowGrabber.WindowGrabber import WindowGrabber
    from src.backend.GnomeExtensions import GnomeExtensions
    from src.windows.Store.Store import Store
    from src.backend.PermissionManagement.FlatpakPermissionManager import FlatpakPermissionManager
    from src.windows.PageManager.PageManager import PageManager
    from src.backend.LockScreenManager.LockScreenManager import LockScreenManager
    from src.tray import TrayIcon


top_level_dir:str = os.path.dirname(__file__)
lm:"LocaleManager" = None
media_manager:"MediaManager" = None #MediaManager
asset_manager_backend:"AssetManagerBackend" = None #AssetManager
asset_manager: "AssetManager" = None
page_manager_window: "PageManager" = None # Only if opened
page_manager:"PageManagerBackend" = None #PageManager #TODO: Rename to page_manager_backend in 2.0.0
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
lock_screen_detector: "LockScreenDetector" = None
store: "Store" = None # Only if opened
flatpak_permission_manager: "FlatpakPermissionManager" = None
threads_running: bool = True
app_loading_finished_tasks: callable = []
api_page_requests: dict[str, str] = {} # Stores api page requests made my --change-page
tray_icon: "TrayIcon" = None
fallback_font: str = find_fallback_font()

app_version: str = "1.5.0-beta.7" # In breaking.feature.fix-state format
exact_app_version_check: bool = False
logs: list[str] = []

release_notes: str = """
<ul>
    <li>Fix: Crash if label is not a string</li>
    <li>Feat: Use git to download plugins in dev mode</li>
    <li>Fix: Error launching action backend in terminal</li>
    <li>Feat: Add Spanish translations</li>
    <li>Fix: Swipes not working for Stream Deck Plus</li>
    <li>Fix: Error when image size is 0</li>
    <li>Fix: Error on X11 when decoding the active window</li>
    <li>Fix: Not blocking action labels and images during screensaver</li>
    <li>Fix: Not reloading page after plugin uninstall</li>
    <li>Fix: Error when XDG_CURRENT_DESKTOP is not set</li>
    <li>Fix: Font weights not stored</li>
    <li>Fix: Removing action not updating input on active page</li>
    <li>Fix: Not always uninstalling plugins correctly</li>
    <li>Fix: Crash when streamdeck-ui has no states key</li>
    <li>Feat: Add option to change the outline color of labels</li>
    <li>Feat: Add default font for labels</li>
    <li>Fix: Registering dial and touch event when used to wake up</li>
    <li>Feat: Add link to wiki when no decks are being detected</li>
    <li>Fix: Not loading screen brightness from page</li>
    <li>Fix: Ignoring font font styles and weights</li>
    <li>Feat: New option to configure default font</li>
    <li>Fix: Decks not always reconnecting</li>
    <li>Fix: Error when renaming page to the same name</li>
    <li>Fix: Keeping old page backups indefinitely</li>
    <li>Feat: Add auto page change for swaywm</li>
    <li>Feat: Add support for screensaver under Cinnamon</li>
    <li>Fix: Crash when drag and dropping buttons with actions</li>
    <li>Feat: Add ability to use line breaks in labels</li>
    <li>Fix: Showing "No decks available" in header when no pages are available</li>
    <li>Feat: Add basic support for the Stream Deck Neo (limited to the normal buttons)</li>
    <li>Update dependencies</li>
</ul>
"""