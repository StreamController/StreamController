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
import sys

import globals as gl
from src.cli.list_devices import handle_list_devices
from src.cli.list_pages import handle_list_pages

MAX_REASONABLE_X = 10
MAX_REASONABLE_Y = 10


def handle_listing_commands():
    """
    Handle --list-devices and --list-pages commands
    Returns True if a listing command was handled, False otherwise
    """
    args = gl.argparser.parse_args()

    if args.list_devices:
        return handle_list_devices()

    if args.list_pages:
        return handle_list_pages()

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

    import dbus

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
