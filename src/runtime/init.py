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
import asyncio
import os
import sys
import time

import usb.core
import usb.util
from StreamDeck.DeviceManager import DeviceManager
from loguru import logger as log

import globals as gl
from locales.LocaleManager import LocaleManager
from src.backend.AssetManagerBackend import AssetManagerBackend
from src.backend.GnomeExtensions import GnomeExtensions
from src.backend.IconPackManagement.IconPackManager import IconPackManager
from src.backend.LockScreenManager.LockScreenManager import LockScreenManager
from src.backend.Logger import Logger, LoggerConfig, Loglevel
from src.backend.MediaManager import MediaManager
from src.backend.Migration.MigrationManager import MigrationManager
from src.backend.Migration.Migrators.Migrator_1_5_0 import Migrator_1_5_0
from src.backend.Migration.Migrators.Migrator_1_5_0_beta_5 import Migrator_1_5_0_beta_5
from src.backend.PageManagement.PageManagerBackend import PageManagerBackend
from src.backend.PermissionManagement.FlatpakPermissionManager import (
    FlatpakPermissionManager,
)
from src.backend.PluginManager.PluginManager import PluginManager
from src.backend.SDPlusBarWallpaperPackManagement.SDPlusBarWallpaperPackManager import (
    SDPlusBarWallpaperPackManager,
)
from src.backend.SettingsManager import SettingsManager
from src.backend.Store.StoreBackend import NoConnectionError, StoreBackend
from src.backend.WallpaperPackManagement.WallpaperPackManager import WallpaperPackManager
from src.backend.Wayland.Wayland import Wayland
from src.backend.WindowGrabber.WindowGrabber import WindowGrabber
from src.Signals.SignalManager import SignalManager
from src.tray import TrayIcon


def write_logs(record):
    gl.logs.append(record)

@log.catch
def config_logger():
    log.remove()
    # Create log files
    log.add(os.path.join(gl.DATA_PATH, "logs/logs.log"), rotation="3 days", backtrace=True, diagnose=True, level="TRACE")
    # Set min level to print
    log.add(sys.stderr, level="TRACE")
    log.add(write_logs, level="TRACE")

    plugin_logger = Logger(
        LoggerConfig(
            name="PLUGIN",
            log_file_path=os.path.join(gl.DATA_PATH, "logs/plugins.log"),
            base_log_level="TRACE",
            rotation="3 days",
            retention=None,
            compression="zip"
        ),
        [
            Loglevel("TRACE", "trace", 5, "<bold><cyan>"),
            Loglevel("DEBUG", "debug", 10, "<bold><blue>"),
            Loglevel("INFO", "info", 20, "<bold><white>"),
            Loglevel("SUCCESS", "success", 25, "<bold><green>"),
            Loglevel("WARNING", "warning", 30, "<bold><yellow>"),
            Loglevel("ERROR", "error", 40, "<red>"),
            Loglevel("CRITICAL", "critical", 50, "<bold><red>"),
        ]
    )

    gl.loggers["plugins"] = plugin_logger

@log.catch
def create_cache_folder():
    os.makedirs(os.path.join(gl.DATA_PATH, "cache"), exist_ok=True)

def create_global_objects(main_path: str):
    # Setup locales
    gl.tray_icon = TrayIcon()
    # gl.tray_icon.run_detached()

    gl.lm = LocaleManager(csv_path=os.path.join(main_path, "locales", "locales.csv"))
    gl.lm.set_to_os_default()
    gl.lm.set_fallback_language("en_US")

    gl.flatpak_permission_manager = FlatpakPermissionManager()

    gl.gnome_extensions = GnomeExtensions()

    gl.settings_manager = SettingsManager()

    gl.signal_manager = SignalManager()

    gl.media_manager = MediaManager()
    gl.asset_manager_backend = AssetManagerBackend()
    gl.page_manager = PageManagerBackend(gl.settings_manager)
    gl.page_manager.remove_old_backups()
    gl.page_manager.backup_pages()
    gl.icon_pack_manager = IconPackManager()
    gl.wallpaper_pack_manager = WallpaperPackManager()
    gl.sd_plus_bar_wallpaper_pack_manager = SDPlusBarWallpaperPackManager()

    # Store
    gl.store_backend = StoreBackend()

    # Plugin Manager
    gl.plugin_manager = PluginManager()
    gl.plugin_manager.load_plugins(show_notification=True)
    gl.plugin_manager.generate_action_index()

    gl.window_grabber = WindowGrabber()

    if os.getenv("WAYLAND_DISPLAY", False):
        gl.wayland = Wayland()

    gl.lock_screen_detector = LockScreenManager()

    
    # gl.dekstop_grabber = DesktopGrabber()

@log.catch
def update_assets():
    settings = gl.settings_manager.load_settings_from_file(os.path.join(gl.DATA_PATH, "settings", "settings.json"))
    auto_update = settings.get("store", {}).get("auto-update", True)

    if gl.argparser.parse_args().devel:
        auto_update = False

    if not auto_update:
        log.info("Skipping store asset update")
        return

    log.info("Updating store assets")
    start = time.time()
    number_of_installed_updates = asyncio.run(gl.store_backend.update_everything())
    if isinstance(number_of_installed_updates, NoConnectionError):
        log.error("Failed to update store assets")
        if hasattr(gl.app, "main_win"):
            gl.app.main_win.show_error_toast("Failed to update store assets")
        return
    log.info(f"Updating {number_of_installed_updates} store assets took {time.time() - start} seconds")

    if number_of_installed_updates <= 0:
        return

    # Show toast in ui
    if hasattr(gl.app, "main_win"):
        gl.app.main_win.show_info_toast(f"{number_of_installed_updates} assets updated")

@log.catch
def reset_all_decks():
    # Find all USB devices
    devices = usb.core.find(find_all=True, idVendor=DeviceManager.USB_VID_ELGATO)
    for device in devices:
        try:
            # Check if it's a StreamDeck
            if device.idProduct in [
                DeviceManager.USB_PID_STREAMDECK_ORIGINAL,
                DeviceManager.USB_PID_STREAMDECK_ORIGINAL_V2,
                DeviceManager.USB_PID_STREAMDECK_MINI,
                DeviceManager.USB_PID_STREAMDECK_XL,
                DeviceManager.USB_PID_STREAMDECK_MK2,
                DeviceManager.USB_PID_STREAMDECK_PEDAL,
                DeviceManager.USB_PID_STREAMDECK_PLUS,
                DeviceManager.USB_PID_STREAMDECK_MK2_SCISSOR,
                DeviceManager.USB_PID_STREAMDECK_MK2_MODULE,
                DeviceManager.USB_PID_STREAMDECK_MINI_MK2_MODULE,
                DeviceManager.USB_PID_STREAMDECK_XL_V2_MODULE,
            ]:
                # Reset deck
                usb.util.dispose_resources(device)
                device.reset()
        except:
            log.error("Failed to reset deck, maybe it's already connected to another instance? Skipping...")


def quit_running():
    if gl.IS_MAC:
        return

    import dbus

    log.info("Checking if another instance is running")
    session_bus = dbus.SessionBus()
    obj: dbus.BusObject = None
    action_interface: dbus.Interface = None
    try:
        obj = session_bus.get_object("com.core447.StreamController", "/com/core447/StreamController")
        action_interface = dbus.Interface(obj, "org.gtk.Actions")
    except dbus.exceptions.DBusException as e:
        log.info("No other instance running, continuing")
        log.error(e)
    except ValueError as e:
        log.info("The last instance has not been properly closed, continuing... This may cause issues")

    if None not in [obj, action_interface]:
        if gl.argparser.parse_args().close_running:
            log.info("Closing running instance")
            try:
                action_interface.Activate("quit", [], [])
            except dbus.exceptions.DBusException as e:
                if "org.freedesktop.DBus.Error.NoReply" in str(e):
                    log.error("Could not close running instance: " + str(e))
                    sys.exit(0)
            time.sleep(5)

        else:
            action_interface.Activate("reopen", [], [])
            log.info("Already running, exiting")
            sys.exit(0)


def setup_migrations():
    """Run all migrators."""
    migration_manager = MigrationManager()
    # Add migrators
    migration_manager.add_migrator(Migrator_1_5_0())
    migration_manager.add_migrator(Migrator_1_5_0_beta_5())
    # Run migrators
    migration_manager.run_migrators()
