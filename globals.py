import Pyro5.api
import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.app import App
    from locales.LocaleManager import LocaleManager
    from src.backend.AssetManager import AssetManager
    from src.backend.MediaManager import MediaManager
    from src.backend.PageManagement.PageManager import PageManager
    from src.backend.SettingsManager import SettingsManager
    from src.backend.DeckManagement.DeckManager import DeckManager
    from src.backend.PluginManager.PluginManager import PluginManager
    from src.backend.IconPackManagement.IconPackManager import IconPackManager
    from src.backend.WallpaperPackManagement.WallpaperPackManager import WallpaperPackManager
    from src.windows.Store.StoreBackend import StoreBackend

top_level_dir:str = os.path.dirname(__file__)
lm:"LocaleManager" = None
media_manager:"MediaManager" = None #MediaManager
asset_manager:"AssetManager" = None #AssetManager
page_manager:"PageManager" = None #PageManager
settings_manager:"SettingsManager" = None #SettingsManager
app:"App" = None #App
deck_manager:"DeckManager" = None #DeckManager
plugin_manager:"PluginManager" = None #PluginManager
video_extensions = ["mp4", "mov", "MP4", "MOV", "mkv", "MKV", "webm", "WEBM", "gif", "GIF"]
image_extensions = ["png", "jpg", "jpeg"]
icon_pack_manager: "IconPackManager" = None
wallpaper_pack_manager: "WallpaperPackManager" = None
store_backend: "StoreBackend" = None
pyro_daemon: Pyro5.api.Daemon = None
app_version: str = "0.0.2-alpha"