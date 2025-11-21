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

import usb.core
import usb.util
from StreamDeck.DeviceManager import DeviceManager

# Import globals first to get IS_MAC
import globals as gl

if not gl.IS_MAC:
    import dbus
    import dbus.service
    from dbus.mainloop.glib import DBusGMainLoop

# Import own modules
from src.app import App
from src.backend.DeckManagement.DeckManager import DeckManager
from locales.LocaleManager import LocaleManager
from src.backend.MediaManager import MediaManager
from src.backend.AssetManagerBackend import AssetManagerBackend
from src.backend.PageManagement.PageManagerBackend import PageManagerBackend
from src.backend.SettingsManager import SettingsManager
from src.backend.PluginManager.PluginManager import PluginManager
from src.backend.IconPackManagement.IconPackManager import IconPackManager
from src.backend.WallpaperPackManagement.WallpaperPackManager import WallpaperPackManager
from src.backend.Store.StoreBackend import StoreBackend, NoConnectionError
from autostart import setup_autostart
from src.Signals.SignalManager import SignalManager
from src.backend.WindowGrabber.WindowGrabber import WindowGrabber
from src.backend.GnomeExtensions import GnomeExtensions
from src.backend.PermissionManagement.FlatpakPermissionManager import FlatpakPermissionManager
from src.backend.Wayland.Wayland import Wayland
from src.backend.LockScreenManager.LockScreenManager import LockScreenManager
from src.tray import TrayIcon
from src.backend.Logger import Logger, LoggerConfig, Loglevel

# Migration
from src.backend.Migration.MigrationManager import MigrationManager
from src.backend.Migration.Migrators.Migrator_1_5_0 import Migrator_1_5_0
from src.backend.Migration.Migrators.Migrator_1_5_0_beta_5 import Migrator_1_5_0_beta_5

# Import globals
import globals as gl

# Define constants
DEFAULT_DATA_PATH = os.path.expanduser("~/.var/app/com.core447.StreamController/data")
MAX_REASONABLE_X = 10
MAX_REASONABLE_Y = 10

main_path = os.path.abspath(os.path.dirname(__file__))
gl.MAIN_PATH = main_path

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

def create_global_objects():
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

    # Initialize thread pool manager
    from src.backend.ThreadPoolManager import ThreadPoolManager
    gl.thread_pool = ThreadPoolManager()

    gl.media_manager = MediaManager()
    gl.asset_manager_backend = AssetManagerBackend()
    gl.page_manager = PageManagerBackend(gl.settings_manager)
    gl.page_manager.remove_old_backups()
    gl.page_manager.backup_pages()
    gl.icon_pack_manager = IconPackManager()
    gl.wallpaper_pack_manager = WallpaperPackManager()

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

def handle_listing_commands():
    """
    Handle --list-devices and --list-pages commands
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
    
    if args.list_pages:
        print("Scanning for available pages...")
        print()
        
        try:
            # Try to get pages from the file system
            import os
            data_path = gl.DATA_PATH if hasattr(gl, 'DATA_PATH') else DEFAULT_DATA_PATH
            pages_dir = os.path.join(data_path, "pages")
            
            if not os.path.exists(pages_dir):
                print(f"Pages directory not found: {pages_dir}")
                print("\nThis might mean StreamController hasn't been set up yet.")
                return True
            
            page_files = [f for f in os.listdir(pages_dir) if f.endswith('.json') and not f.startswith('.')]
            
            if not page_files:
                print("No pages found.")
                print(f"\nPages should be located in: {pages_dir}")
                return True
            
            print(f"Found {len(page_files)} page(s):")
            print()
            
            for page_file in sorted(page_files):
                page_name = os.path.splitext(page_file)[0]
                page_path = os.path.join(pages_dir, page_file)
                
                try:
                    # Try to read basic info from the page file
                    import json
                    with open(page_path, 'r') as f:
                        page_data = json.load(f)
                    
                    print(f"  {page_name}")
                    
                    # Count items with states
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
                    
        except Exception as e:
            print(f"Error scanning pages: {e}")
        
        return True
    
    return False

def validate_state_change_args(args):
    """
    Validate CLI arguments for --change-state
    Returns (is_valid, error_message)
    """
    if not args.change_state:
        return True, None
    
    for i, (serial_number, page_name, coords, state_number) in enumerate(args.change_state):
        # Validate serial number format (basic check)
        if not serial_number or not isinstance(serial_number, str):
            return False, f"Invalid serial number in argument {i+1}: '{serial_number}'"
        
        # Validate page name
        if not page_name or not isinstance(page_name, str):
            return False, f"Invalid page name in argument {i+1}: '{page_name}'"
        
        # Validate coordinate format
        if not coords or not isinstance(coords, str):
            return False, f"Invalid coordinates in argument {i+1}: '{coords}'"
        
        if ',' not in coords:
            return False, f"Invalid coordinate format in argument {i+1}: '{coords}'. Expected format: 'x,y' (e.g., '0,0')"
        
        try:
            x, y = map(int, coords.split(','))
            if x < 0 or y < 0:
                return False, f"Coordinates must be non-negative in argument {i+1}: '{coords}'"
            if x > MAX_REASONABLE_X or y > MAX_REASONABLE_Y:  # Reasonable bounds check
                return False, f"Coordinates seem too large in argument {i+1}: '{coords}'. Most StreamDecks have coordinates 0-4"
        except ValueError:
            return False, f"Invalid coordinate format in argument {i+1}: '{coords}'. Expected integers like '0,0'"
        
        # Validate state number
        try:
            state_num = int(state_number)
            if state_num < 0:
                return False, f"State number must be non-negative in argument {i+1}: '{state_number}'"
            if state_num > 20:  # Reasonable bounds check
                return False, f"State number seems too large in argument {i+1}: '{state_number}'. Most items have 1-5 states"
        except ValueError:
            return False, f"Invalid state number in argument {i+1}: '{state_number}'. Must be an integer"
    
    return True, None

def make_api_calls():
    if gl.IS_MAC:
        return False
        
    args = gl.argparser.parse_args()
    has_page_requests = args.change_page
    has_state_requests = args.change_state
    
    if not has_page_requests and not has_state_requests:
        return False
    
    # Validate state change arguments before proceeding
    if has_state_requests:
        is_valid, error_msg = validate_state_change_args(args)
        if not is_valid:
            print(f"Error: {error_msg}", file=sys.stderr)
            print("\nUsage examples:", file=sys.stderr)
            print("  --change-state CL123456789 Main 0,0 1", file=sys.stderr)
            print("  --change-state CL123456789 Soundboard 2,1 0", file=sys.stderr)
            print("\nParameters:", file=sys.stderr)
            print("  SERIAL_NUMBER: Device serial (e.g., CL123456789)", file=sys.stderr)
            print("  PAGE_NAME: Page name (e.g., Main, Soundboard)", file=sys.stderr)
            print("  COORDINATES: Position as x,y (e.g., 0,0 for top-left)", file=sys.stderr)
            print("  STATE_NUMBER: State to change to (e.g., 0, 1, 2)", file=sys.stderr)
            sys.exit(1)
    
    session_bus = dbus.SessionBus()
    obj: dbus.BusObject = None
    action_interface: dbus.Interface = None
    try:
        obj = session_bus.get_object("com.core447.StreamController", "/com/core447/StreamController")
        action_interface = dbus.Interface(obj, "org.gtk.Actions")
    except dbus.exceptions.DBusException as e:
        obj = None
    except ValueError as e:
        obj = None

    # Handle page change requests
    if has_page_requests:
        for serial_number, page_name in args.change_page:
            if None in [obj, action_interface] or args.close_running:
                gl.api_page_requests[serial_number] = page_name
            else:
                # Other instance is running - call dbus interfaces
                action_interface.Activate("change_page", [[serial_number, page_name]], [])
                return True

    # Handle state change requests
    if has_state_requests:
        for serial_number, page_name, coords, state_number in args.change_state:
            if None in [obj, action_interface] or args.close_running:
                try:
                    state_num = int(state_number)
                    gl.api_state_requests[serial_number] = {
                        "page_name": page_name,
                        "coords": coords,
                        "state": state_num
                    }
                except ValueError:
                    print(f"Error: Invalid state number '{state_number}'. Must be an integer.", file=sys.stderr)
                    sys.exit(1)
            else:
                # Other instance is running - call dbus interfaces
                action_interface.Activate("change_state", [[serial_number, page_name, coords, state_number]], [])
                return True

    return False


    
@log.catch
def main():
    # Handle listing commands first (they don't need full initialization)
    if handle_listing_commands():
        return
    
    if make_api_calls():
        return

    gsk_render_env_var = os.environ.get("GSK_RENDERER")
    if gsk_render_env_var != "ngl":
        log.warning('Should you get an Gtk X11 error preventing the app from starting please add '
                    'GSK_RENDERER=ngl to your "/etc/environment" file')

    if not gl.IS_MAC:
        DBusGMainLoop(set_as_default=True)
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
    gl.thread_pool.submit_network_task(update_assets)
    load()

if __name__ == "__main__":
    main()


log.trace("Reached end of main.py")
