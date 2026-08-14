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
# Answer the command from an already running instance before anything heavy is
# imported - see src/CLI.py. Everything below costs ~2.4s to import, which
# otherwise dwarfs the DBus call itself and makes the CLI unusable for scripting.
import sys
from src.CLI import run_against_running_instance

if run_against_running_instance():
    sys.exit(0)

# Import Python modules
import setproctitle

setproctitle.setproctitle("StreamController")

# "install" patches
from src.patcher.patcher import Patcher
patcher = Patcher()
patcher.patch()

import sys
from loguru import logger as log
import os
import time
import asyncio
import threading
import json

import usb.core
import usb.util
from StreamDeck.DeviceManager import DeviceManager
from StreamDeck.ProductIDs import USBProductIDs, USBVendorIDs

# Import globals first to get IS_MAC
import globals as gl

if not gl.IS_MAC:
    # dbus-python is used for blocking method calls only, so its GLib main loop
    # is deliberately never installed. Attaching a connection to the main loop
    # makes dbus-python rebuild that connection's GSources from whichever thread
    # sends a message, which corrupts them once anything calls D-Bus off the
    # main thread. Use GDBus (Gio) for signals and exported objects instead.
    import dbus

# Import own modules
from src.app import App
from src.backend.DeckManagement.DeckManager import DeckManager
from locales.LocaleManager import LocaleManager
from src.backend.MediaManager import MediaManager
from src.backend.AssetManagerBackend import AssetManagerBackend
from src.backend.PageManagement.PageManagerBackend import PageManagerBackend
from src.backend.PageManagement import HeadlessPageOps as ops
from src.CLI import (print_get_results, print_emulate_input_usage, print_state_change_usage,
                     validate_emulate_input_args, validate_state_change_args)
from src.backend.SettingsManager import SettingsManager
from src.backend.AI.AIManager import AIManager
from src.backend.AI.ActionDocs import ActionDocRegistry
from src.backend.PluginManager.PluginManager import PluginManager
from src.backend.IconPackManagement.IconPackManager import IconPackManager
from src.backend.WallpaperPackManagement.WallpaperPackManager import WallpaperPackManager
from src.backend.SDPlusBarWallpaperPackManagement.SDPlusBarWallpaperPackManager import SDPlusBarWallpaperPackManager
from src.backend.Store.StoreBackend import StoreBackend, NoConnectionError
from autostart import setup_autostart
from src.Signals.SignalManager import SignalManager
from src.backend.WindowGrabber.WindowGrabber import WindowGrabber
from src.backend.GnomeExtensions import GnomeExtensions
from src.backend.PermissionManagement.FlatpakPermissionManager import FlatpakPermissionManager
from src.backend.Wayland.Wayland import Wayland
from src.backend.LockScreenManager.LockScreenManager import LockScreenManager
from src.tray import TrayIcon
from src.backend.Logger import Logger, LoggerConfig, Loglevel, intercept_stdlib_logging
from src.backend import LogRedaction

# Migration
from src.backend.Migration.MigrationManager import MigrationManager
from src.backend.Migration.Migrators.Migrator_1_5_0 import Migrator_1_5_0
from src.backend.Migration.Migrators.Migrator_1_5_0_beta_5 import Migrator_1_5_0_beta_5

# Import globals
import globals as gl

# Define constants
DEFAULT_DATA_PATH = os.path.expanduser("~/.var/app/com.core447.StreamController/data")

main_path = os.path.abspath(os.path.dirname(__file__))
gl.MAIN_PATH = main_path

def write_logs(record):
    gl.logs.append(record)

@log.catch
def config_logger():
    log.remove()
    # Keep the user's username, hostname and the hosts plugins talk to out of
    # the logs they paste into bug reports - covers every sink below at once
    log.configure(patcher=LogRedaction.patch_record)
    # Create log files
    log.add(os.path.join(gl.DATA_PATH, "logs/logs.log"), rotation="3 days", backtrace=True, diagnose=True, level="TRACE")
    # Set min level to print
    log.add(sys.stderr, level="TRACE")
    log.add(write_logs, level="TRACE")

    # The streamdeck library logs its deck reconnect diagnostics through the
    # standard logging module, which loguru does not pick up on its own
    intercept_stdlib_logging()

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

class Main:
    def __init__(self, application_id, deck_manager):
        # Launch gtk application
        self.app = App(application_id=application_id, deck_manager=deck_manager)

        gl.app = self.app

        self.app.run(gl.argparser.parse_args().app_args)

@log.catch
def load():
    log.info("Loading app")
    gl.deck_manager = DeckManager()
    gl.deck_manager.load_decks()
    gl.main = Main(application_id="com.core447.StreamController", deck_manager=gl.deck_manager)

@log.catch
def create_cache_folder():
    os.makedirs(os.path.join(gl.DATA_PATH, "cache"), exist_ok=True)

def get_referenced_plugin_ids_from_pages() -> set[str]:
    plugin_ids: set[str] = set()
    pages_dir = os.path.join(gl.DATA_PATH, "pages")
    page_settings_path = os.path.join(gl.DATA_PATH, "settings", "pages.json")

    selected_pages: set[str] = set()
    if os.path.isfile(page_settings_path):
        try:
            with open(page_settings_path, "r") as f:
                settings = json.load(f)
            for page_path in settings.get("default-pages", {}).values():
                if isinstance(page_path, str) and page_path.endswith(".json"):
                    if os.path.isabs(page_path):
                        selected_pages.add(page_path)
                    else:
                        selected_pages.add(os.path.join(pages_dir, os.path.basename(page_path)))
        except Exception as e:
            log.warning(f"Failed to parse default pages for plugin preload: {e}")

    if not selected_pages and os.path.isdir(pages_dir):
        for name in os.listdir(pages_dir):
            if name.endswith(".json"):
                selected_pages.add(os.path.join(pages_dir, name))

    for page_path in selected_pages:
        if not os.path.isfile(page_path):
            continue
        try:
            with open(page_path, "r") as f:
                page_data = json.load(f)
        except Exception:
            continue

        for input_type in ("keys", "dials", "touchscreens"):
            for input_cfg in page_data.get(input_type, {}).values():
                for state_cfg in input_cfg.get("states", {}).values():
                    for action in state_cfg.get("actions", []):
                        if not isinstance(action, dict):
                            continue
                        action_id = action.get("id")
                        if isinstance(action_id, str) and "::" in action_id:
                            plugin_ids.add(action_id.split("::")[0])

    return plugin_ids

def initialize_deferred_services():
    if gl.asset_manager_backend is None:
        gl.asset_manager_backend = AssetManagerBackend()
    if gl.icon_pack_manager is None:
        gl.icon_pack_manager = IconPackManager()
    if gl.wallpaper_pack_manager is None:
        gl.wallpaper_pack_manager = WallpaperPackManager()
    if gl.sd_plus_bar_wallpaper_pack_manager is None:
        gl.sd_plus_bar_wallpaper_pack_manager = SDPlusBarWallpaperPackManager()
    if gl.store_backend is None:
        gl.store_backend = StoreBackend()

def create_global_objects():
    args = gl.argparser.parse_args()

    # Setup locales
    gl.tray_icon = TrayIcon()
    # gl.tray_icon.run_detached()

    gl.lm = LocaleManager(csv_path=os.path.join(main_path, "locales", "locales.csv"))
    gl.lm.set_to_os_default()
    gl.lm.set_fallback_language("en_US")

    gl.flatpak_permission_manager = FlatpakPermissionManager()

    gl.gnome_extensions = GnomeExtensions()

    gl.settings_manager = SettingsManager()

    gl.ai_manager = AIManager()
    gl.action_doc_registry = ActionDocRegistry()

    gl.signal_manager = SignalManager()

    gl.media_manager = MediaManager()
    gl.page_manager = PageManagerBackend(gl.settings_manager)
    gl.page_manager.remove_old_backups()
    gl.page_manager.backup_pages()
    if args.daemon_only:
        gl.page_manager.set_pages_to_cache(0)
    else:
        initialize_deferred_services()

    # Plugin Manager
    gl.plugin_manager = PluginManager()
    if args.daemon_only:
        plugin_ids = get_referenced_plugin_ids_from_pages()
        gl.plugin_manager.load_plugins(show_notification=False, plugin_ids=plugin_ids)
        log.info(f"Daemon-only plugin preload: loaded {len(plugin_ids)} referenced plugin(s)")
    else:
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
    devices = usb.core.find(find_all=True, idVendor=USBVendorIDs.USB_VID_ELGATO)
    for device in devices:
        try:
            # Check if it's a StreamDeck
            if device.idProduct in [
                USBProductIDs.USB_PID_STREAMDECK_ORIGINAL,
                USBProductIDs.USB_PID_STREAMDECK_ORIGINAL_V2,
                USBProductIDs.USB_PID_STREAMDECK_MINI,
                USBProductIDs.USB_PID_STREAMDECK_XL,
                USBProductIDs.USB_PID_STREAMDECK_MK2,
                USBProductIDs.USB_PID_STREAMDECK_PEDAL,
                USBProductIDs.USB_PID_STREAMDECK_PLUS,
                USBProductIDs.USB_PID_STREAMDECK_MK2_SCISSOR,
                USBProductIDs.USB_PID_STREAMDECK_MK2_MODULE,
                USBProductIDs.USB_PID_STREAMDECK_MINI_MK2_MODULE,
                USBProductIDs.USB_PID_STREAMDECK_XL_V2_MODULE,
            ]:
                # Reset deck
                usb.util.dispose_resources(device)
                device.reset()
        except:
            log.error("Failed to reset deck, maybe it's already connected to another instance? Skipping...")

def quit_running():
    if gl.IS_MAC:
        return
        
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

def find_page_file(pages_dir, page_name):
    """
    Resolve a page name to its json file path by scanning pages_dir directly,
    without needing a fully initialized PageManagerBackend.
    """
    if os.path.isfile(page_name):
        return page_name

    if not os.path.exists(pages_dir):
        return None

    target_name = page_name.lower()
    for page_file in os.listdir(pages_dir):
        if not page_file.endswith(".json"):
            continue
        base_no_ext = os.path.splitext(page_file)[0]
        if page_file.lower() == target_name or base_no_ext.lower() == target_name:
            return os.path.join(pages_dir, page_file)

    return None

def _headless_page_path(name: str) -> str:
    path = ops.resolve_page_path(name)
    if path is None:
        raise ops.HeadlessOpError(f"Page '{name}' not found")
    return path

def handle_listing_commands():
    """
    Handle --list-devices, --list-pages and --list-actions commands
    Returns True if a listing command was handled, False otherwise
    """
    args = gl.argparser.parse_args()
    
    if args.list_devices:
        print("Scanning for connected StreamDeck devices...")
        print()
        
        # We need to initialize deck manager to scan for devices
        try:
            # Minimal initialization to scan for devices
            from StreamDeck.DeviceManager import DeviceManager
            devices = DeviceManager().enumerate()
            
            if not devices:
                print("No StreamDeck devices found.")
                print("\nTips:")
                print("- Make sure your StreamDeck is connected via USB")
                print("- Check that the device is recognized by your system")
                print("- Try running with sudo if you have permission issues")
                return True
            
            print(f"Found {len(devices)} StreamDeck device(s):")
            print()
            
            for i, device in enumerate(devices):
                print(f"Device {i+1}:")
                try:
                    # Try to get basic info without opening if possible
                    device_id = getattr(device, 'id', lambda: 'Unknown')()
                    print(f"  Device ID: {device_id}")
                    
                    # Try to get info that doesn't require opening the device
                    try:
                        deck_type = getattr(device, 'deck_type', lambda: 'Unknown StreamDeck')()
                        print(f"  Product Name: {deck_type}")
                    except:
                        print(f"  Product Name: Unknown (permission issue)")
                    
                    # Try to open device to get detailed info
                    device_opened = False
                    try:
                        if not device.is_open():
                            device.open()
                            device_opened = True
                        
                        print(f"  Serial Number: {device.get_serial_number()}")
                        key_layout = device.key_layout()
                        print(f"  Key Layout: {key_layout[1]}x{key_layout[0]} ({device.key_count()} keys)")
                        
                        if hasattr(device, 'dial_count') and device.dial_count() > 0:
                            print(f"  Dials: {device.dial_count()}")
                        if hasattr(device, 'is_touch') and device.is_touch():
                            print(f"  Touchscreen: Yes")
                        print(f"  Connected: {'Yes' if device.connected() else 'No'}")
                        
                        if device_opened:
                            device.close()
                            
                    except PermissionError:
                        print(f"  Status: Permission denied")
                        print(f"  Note: Run 'sudo python main.py --list-devices' or install udev rules")
                    except Exception as open_error:
                        print(f"  Status: Could not access device ({open_error})")
                        print(f"  Note: This may be a permission issue or device is in use")
                        
                except Exception as e:
                    print(f"  Error: {e}")
                    if "permission" in str(e).lower() or "access" in str(e).lower():
                        print(f"  Note: Try running with sudo or install proper udev rules")
                
                print()
        except ImportError:
            print("Error: StreamDeck library not available")
        except Exception as e:
            print(f"Error scanning devices: {e}")
        
        # Add helpful information about permissions
        print("\nTroubleshooting:")
        print("- If you see permission errors, try: sudo python main.py --list-devices")
        print("- For permanent fix, install udev rules: sudo cp udev.rules /etc/udev/rules.d/70-streamdeck.rules")
        print("- Then run: sudo udevadm control --reload-rules && sudo udevadm trigger")
        print("- After installing udev rules, unplug and replug your StreamDeck")
        
        return True
    
    if args.list_actions:
        data_path = gl.DATA_PATH if hasattr(gl, 'DATA_PATH') else DEFAULT_DATA_PATH
        pages_dir = os.path.join(data_path, "pages")

        json_results = []

        for page_name, coords, state_number in args.list_actions:
            entry = {"page": page_name, "coords": coords, "state": state_number}

            if not args.json:
                print(f"Actions for page '{page_name}', key {coords}, state {state_number}:")

            page_path = find_page_file(pages_dir, page_name)
            if page_path is None:
                entry["error"] = f"Page '{page_name}' not found in {pages_dir}"
                if not args.json:
                    print(f"  Error: {entry['error']}")
                    print()
                json_results.append(entry)
                continue

            try:
                x, y = map(int, coords.split(','))
            except (ValueError, AttributeError):
                entry["error"] = f"Invalid coordinate format '{coords}'. Expected format: 'x,y' (e.g., '0,0')"
                if not args.json:
                    print(f"  {entry['error']}")
                    print()
                json_results.append(entry)
                continue
            json_identifier = f"{x}x{y}"

            try:
                with open(page_path, 'r') as f:
                    page_data = json.load(f)
            except Exception as e:
                entry["error"] = f"Error reading page: {e}"
                if not args.json:
                    print(f"  {entry['error']}")
                    print()
                json_results.append(entry)
                continue

            key_data = page_data.get("keys", {}).get(json_identifier)
            if key_data is None:
                entry["error"] = f"No key configured at {coords}"
                if not args.json:
                    print(f"  {entry['error']}")
                    print()
                json_results.append(entry)
                continue

            state_data = key_data.get("states", {}).get(state_number)
            if state_data is None:
                available_states = sorted(key_data.get("states", {}).keys(), key=int)
                entry["error"] = f"State {state_number} does not exist. Available states: {', '.join(available_states) or 'none'}"
                entry["available_states"] = available_states
                if not args.json:
                    print(f"  {entry['error']}")
                    print()
                json_results.append(entry)
                continue

            actions = state_data.get("actions", [])
            entry["actions"] = [a.get("id", "unknown") for a in actions]
            json_results.append(entry)

            if not args.json:
                if not actions:
                    print("  No actions configured")
                else:
                    for i, action in enumerate(actions):
                        print(f"  [{i}] {action.get('id', 'unknown')}")
                print()

        if args.json:
            print(json.dumps(json_results, indent=2))
        else:
            print("Trigger one of these with, e.g.:")
            print("  --emulate-input press SERIAL PAGE COORDS")
            print("  --emulate-input long-press SERIAL PAGE COORDS")

        return True

    if args.list_pages:
        data_path = gl.DATA_PATH if hasattr(gl, 'DATA_PATH') else DEFAULT_DATA_PATH
        pages_dir = os.path.join(data_path, "pages")

        if not os.path.exists(pages_dir):
            if args.json:
                print(json.dumps({"error": f"Pages directory not found: {pages_dir}", "pages": []}))
            else:
                print(f"Pages directory not found: {pages_dir}")
                print("\nThis might mean StreamController hasn't been set up yet.")
            return True

        page_files = sorted(f for f in os.listdir(pages_dir) if f.endswith('.json') and not f.startswith('.'))

        if args.json:
            print(json.dumps({"pages": [os.path.splitext(f)[0] for f in page_files]}, indent=2))
            return True

        print("Scanning for available pages...")
        print()

        if not page_files:
            print("No pages found.")
            print(f"\nPages should be located in: {pages_dir}")
            return True

        print(f"Found {len(page_files)} page(s):")
        print()

        for page_file in page_files:
            page_name = os.path.splitext(page_file)[0]
            page_path = os.path.join(pages_dir, page_file)

            try:
                with open(page_path, 'r') as f:
                    page_data = json.load(f)

                print(f"  {page_name}")

                items_with_states = 0
                for input_type in ['keys', 'dials', 'touchscreens']:
                    if input_type in page_data:
                        for item_id, item_data in page_data[input_type].items():
                            if 'states' in item_data and item_data['states']:
                                states_count = len(item_data['states'])
                                items_with_states += 1
                                if states_count > 1:
                                    print(f"    - {input_type[:-1]} {item_id}: {states_count} states")

                if items_with_states == 0:
                    print(f"    - No configured items")

            except Exception as e:
                print(f"    - Error reading page: {e}")

            print()

        return True

    if args.get_label:
        results = []
        for page_name, coords, state_number, position, prop in args.get_label:
            entry = {"page": page_name, "coords": coords, "state": state_number, "position": position, "property": prop}
            try:
                page_path = _headless_page_path(page_name)
                entry["value"] = ops.format_value(ops.get_label(page_path, coords, int(state_number), position, prop))
            except (ops.HeadlessOpError, ValueError) as e:
                entry["error"] = str(e)
            results.append(entry)
        print_get_results(results, args.json)
        return True

    if args.get_background_color:
        results = []
        for page_name, coords, state_number in args.get_background_color:
            entry = {"page": page_name, "coords": coords, "state": state_number}
            try:
                page_path = _headless_page_path(page_name)
                entry["value"] = ops.format_value(ops.get_background_color(page_path, coords, int(state_number)))
            except (ops.HeadlessOpError, ValueError) as e:
                entry["error"] = str(e)
            results.append(entry)
        print_get_results(results, args.json)
        return True

    if args.get_icon:
        results = []
        for page_name, coords, state_number in args.get_icon:
            entry = {"page": page_name, "coords": coords, "state": state_number}
            try:
                page_path = _headless_page_path(page_name)
                entry["value"] = ops.format_value(ops.get_media(page_path, coords, int(state_number), "path"))
            except (ops.HeadlessOpError, ValueError) as e:
                entry["error"] = str(e)
            results.append(entry)
        print_get_results(results, args.json)
        return True

    if args.get_icon_layout:
        results = []
        for page_name, coords, state_number, prop in args.get_icon_layout:
            entry = {"page": page_name, "coords": coords, "state": state_number, "property": prop}
            try:
                page_path = _headless_page_path(page_name)
                entry["value"] = ops.format_value(ops.get_media(page_path, coords, int(state_number), prop))
            except (ops.HeadlessOpError, ValueError) as e:
                entry["error"] = str(e)
            results.append(entry)
        print_get_results(results, args.json)
        return True

    return False

def buffer_api_requests():
    """
    Stashes --change-page/--change-state/--emulate-input for the instance this
    process is about to become, in gl.api_*_requests (applied once the decks are
    loaded). When an instance is already running these never get here: src/CLI.py
    calls it over DBus and exits long before main.py is imported. The exception
    is --close-running, where the request is meant for the replacement instance.
    """
    if gl.IS_MAC:
        return False

    args = gl.argparser.parse_args()
    if not args.change_page and not args.change_state and not args.emulate_input:
        return False

    is_valid, error_msg = validate_state_change_args(args)
    if not is_valid:
        print(f"Error: {error_msg}", file=sys.stderr)
        print_state_change_usage()
        sys.exit(1)

    is_valid, error_msg = validate_emulate_input_args(args)
    if not is_valid:
        print(f"Error: {error_msg}", file=sys.stderr)
        print_emulate_input_usage()
        sys.exit(1)

    for serial_number, page_name in args.change_page or []:
        gl.api_page_requests[serial_number] = page_name

    for serial_number, page_name, coords, state_number in args.change_state or []:
        try:
            state_num = int(state_number)
        except ValueError:
            print(f"Error: Invalid state number '{state_number}'. Must be an integer.", file=sys.stderr)
            sys.exit(1)
        gl.api_state_requests[serial_number] = {
            "page_name": page_name,
            "coords": coords,
            "state": state_num
        }

    for event, serial_number, page_name, coords in args.emulate_input or []:
        gl.api_action_requests[serial_number] = {
            "event": event,
            "page_name": page_name,
            "coords": coords,
        }

    return False


def _report_error(e: Exception) -> None:
    print(f"Error: {e}", file=sys.stderr)


def handle_extended_commands():
    """
    Handles every mutation/read flag introduced alongside --change-page/
    --change-state/--emulate-input: page CRUD, state add/remove, label,
    background color, icon/media, icon layout, brightness, sleep/wake, export.

    This is the no-instance-running path: it edits the page json directly
    (HeadlessPageOps) and exits, without booting the app. When an instance *is*
    running none of this executes - src/CLI.py answers the same flags over DBus
    before main.py is even imported, so the running instance applies them live.
    Brightness/sleep/wake have no meaningful offline equivalent beyond writing
    the deck settings, since there is no deck to act on.
    """
    if gl.IS_MAC:
        return False

    args = gl.argparser.parse_args()

    flags = (
        args.create_page, args.delete_page, args.rename_page, args.duplicate_page,
        args.export_page, args.export_all, args.add_state, args.remove_state,
        args.set_label, args.set_background_color,
        args.set_icon, args.set_icon_layout,
        args.get_brightness, args.set_brightness, args.sleep, args.wake,
    )
    if not any(flags):
        return False

    had_error = False

    def run(headless_call, live_needed=False):
        nonlocal had_error
        try:
            if live_needed:
                raise ops.HeadlessOpError("StreamController must be running for this command")
            return headless_call()
        except (ops.HeadlessOpError, ValueError) as e:
            _report_error(e)
            had_error = True
            return None

    # ── Page management ─────────────────────────────────────────────

    for (name,) in args.create_page or []:
        run(lambda name=name: ops.create_page(name))

    for (name,) in args.delete_page or []:
        run(lambda name=name: ops.delete_page(_headless_page_path(name)))

    for name, new_name in args.rename_page or []:
        run(lambda name=name, new_name=new_name: ops.rename_page(_headless_page_path(name), new_name))

    for name, new_name in args.duplicate_page or []:
        run(lambda name=name, new_name=new_name: ops.duplicate_page(_headless_page_path(name), new_name))

    for name, dest_path in args.export_page or []:
        dest_path = os.path.abspath(dest_path)
        def _export(name=name, dest_path=dest_path):
            from src.backend.PageManagement import PageBundle
            ops.bootstrap()
            PageBundle.export_page(_headless_page_path(name), dest_path)
        run(_export)
        if not had_error:
            print(f"Exported '{name}' to {dest_path}")

    for (dest_path,) in args.export_all or []:
        dest_path = os.path.abspath(dest_path)
        def _export_all(dest_path=dest_path):
            from src.backend.PageManagement import PageBundle
            from src.backend.Utils.AtomicSaveUtils import atomic_save_json
            ops.bootstrap()
            if dest_path.endswith(".json"):
                pages = {os.path.basename(p): gl.page_manager.get_page_data(p) for p in gl.page_manager.get_pages(add_custom_pages=False)}
                atomic_save_json(dest_path, pages)
            else:
                PageBundle.export_pages(gl.page_manager.get_pages(add_custom_pages=False), dest_path)
        run(_export_all)
        if not had_error:
            print(f"Exported all pages to {dest_path}")

    # ── States ───────────────────────────────────────────────────────

    for name, coords in args.add_state or []:
        new_index = run(lambda name=name, coords=coords: ops.add_state(_headless_page_path(name), coords))
        if new_index is not None:
            print(f"Added state {new_index} to {name} {coords}")

    for name, coords, state in args.remove_state or []:
        run(lambda name=name, coords=coords, state=state: ops.remove_state(_headless_page_path(name), coords, int(state)))

    # ── Labels ───────────────────────────────────────────────────────
    # Reads (--get-label & co) are handled in handle_listing_commands() -
    # they're a plain disk read here, since every mutation below is persisted
    # immediately either way.

    for name, coords, state, position, prop, value in args.set_label or []:
        run(lambda name=name, coords=coords, state=state, position=position, prop=prop, value=value:
            ops.set_label(_headless_page_path(name), coords, int(state), position, prop, value))

    # ── Background color ────────────────────────────────────────────

    for name, coords, state, color in args.set_background_color or []:
        run(lambda name=name, coords=coords, state=state, color=color:
            ops.set_background_color(_headless_page_path(name), coords, int(state), color))

    # ── Icon / media ─────────────────────────────────────────────────

    for name, coords, state, path in args.set_icon or []:
        path = os.path.abspath(path)
        internal_path = run(lambda name=name, coords=coords, state=state, path=path:
                            ops.set_icon(_headless_page_path(name), coords, int(state), path))
        if internal_path is not None:
            print(f"Set icon for {name} {coords} state {state}: {internal_path}")

    for name, coords, state, prop, value in args.set_icon_layout or []:
        run(lambda name=name, coords=coords, state=state, prop=prop, value=value:
            ops.set_media(_headless_page_path(name), coords, int(state), prop, value))

    # ── Brightness ───────────────────────────────────────────────────

    for (serial,) in args.get_brightness or []:
        def _get_brightness(serial=serial):
            ops.bootstrap()
            return gl.settings_manager.get_deck_settings(serial).get("brightness", {}).get("value", 75)
        value = run(_get_brightness)
        if value is not None:
            print(value if args.json else str(value))

    for serial, value in args.set_brightness or []:
        try:
            value_int = int(value)
        except ValueError:
            _report_error(f"Invalid brightness '{value}'. Must be an integer 0-100")
            had_error = True
            continue
        def _set_brightness(serial=serial, value_int=value_int):
            ops.bootstrap()
            settings = gl.settings_manager.get_deck_settings(serial)
            settings.setdefault("brightness", {})["value"] = value_int
            gl.settings_manager.save_deck_settings(serial, settings)
        run(_set_brightness)

    # ── Sleep / wake ─────────────────────────────────────────────────
    # These need a live render loop to actually show/hide the screensaver,
    # so there is no offline equivalent at all.

    for (serial,) in args.sleep or []:
        run(None, live_needed=True)

    for (serial,) in args.wake or []:
        run(None, live_needed=True)

    if had_error:
        sys.exit(1)
    return True


@log.catch
def main():
    args = gl.argparser.parse_args()

    # Handle listing commands first (they don't need full initialization)
    if handle_listing_commands():
        return
    
    if buffer_api_requests():
        return

    if handle_extended_commands():
        return

    gsk_render_env_var = os.environ.get("GSK_RENDERER")
    if gsk_render_env_var != "ngl":
        log.warning('Should you get an Gtk X11 error preventing the app from starting please add '
                    'GSK_RENDERER=ngl to your "/etc/environment" file')

    if not gl.IS_MAC:
        # Dbus
        quit_running()

    reset_all_decks()

    config_logger()

    migration_manager = MigrationManager()
    # Add migrators
    migration_manager.add_migrator(Migrator_1_5_0())
    migration_manager.add_migrator(Migrator_1_5_0_beta_5())
    # Run migrators
    migration_manager.run_migrators()

    create_global_objects()

    app_settings = gl.settings_manager.get_app_settings()
    auto_start = app_settings.get("system", {}).get("autostart", True)
    setup_autostart(auto_start)
    
    create_cache_folder()
    if args.daemon_only:
        log.info("Skipping startup store update thread in daemon-only mode")
    else:
        threading.Thread(target=update_assets, name="update_assets").start()
    load()

if __name__ == "__main__":
    main()