"""
Author: Core447
Year: 2026

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
any later version.

This programm comes with ABSOLUTELY NO WARRANTY!

You should have received a copy of the GNU General Public License
along with this program. If not, see <https://www.gnu.org/licenses/>.
"""
"""
The command line front end, and the fast path that answers it from an already
running instance.

Importing main.py costs ~2.4 s before a single line of CLI code runs: it pulls
in GTK/libadwaita, the deck, plugin and store backends, and - through globals ->
HelperMethods - matplotlib, cairosvg and requests. That is the entire cost of
something like --set-icon; the DBus round trip to the running instance is a few
milliseconds. So run_against_running_instance() is called at the very top of
main.py, before any of those imports, and dispatches straight to the DBus API in
src/api.py using nothing but argparse and dbus-python (~60 ms all in).

Anything this module does not handle - no instance running, --close-running,
macOS, or a flag with no API equivalent such as --list-actions - returns False,
and main.py boots as usual and handles the command itself (editing the page json
directly, buffering page/state changes for the instance it is about to start, or
just launching the app).

The argparser lives here rather than in globals.py for the same reason: the fast
path has to parse the command line without importing globals. globals.py still
owns the `argparser` object itself, so `gl.argparser` keeps working everywhere.

dbus-python is used for blocking method calls only and is never attached to a
main loop - see tests/test_dbus_mainloop.py.
"""
import argparse
import json
import os
import sys

DBUS_NAME = "com.core447.StreamController"
DBUS_PATH = "/com/core447/StreamController"

MAX_REASONABLE_X = 10
MAX_REASONABLE_Y = 10

VALID_EMULATE_INPUT_EVENTS = ("press", "long-press")


def build_argparser() -> argparse.ArgumentParser:
    argparser = argparse.ArgumentParser()
    argparser.add_argument("-b", help="Open in background", action="store_true")
    argparser.add_argument("--daemon-only", help="Run without creating the main window until reopened", action="store_true")
    argparser.add_argument("--devel", help="Developer mode (disables auto update)", action="store_true")
    argparser.add_argument("--skip-load-hardware-decks", help="Skips initilization/use of hardware decks", action="store_true")
    argparser.add_argument("--close-running", help="Close running", action="store_true")
    argparser.add_argument("--data", help="Data path", type=str)
    argparser.add_argument("--json", help="Print machine-readable JSON instead of human-readable text for read/list commands", action="store_true")
    argparser.add_argument("--change-page", action="append", nargs=2, help="Change the page for a device", metavar=("SERIAL_NUMBER", "PAGE_NAME"))
    argparser.add_argument("--list-devices", help="List all connected StreamDeck devices and their properties", action="store_true")
    argparser.add_argument("--list-pages", help="List all available pages", action="store_true")
    argparser.add_argument("--change-state", action="append", nargs=4,
                          help="Change the state of a StreamDeck item. Format: SERIAL PAGE COORDS STATE\n"
                               "  SERIAL: Device serial number (e.g., CL123456789)\n"
                               "  PAGE: Page name (e.g., Main, Soundboard) \n"
                               "  COORDS: Position as x,y (e.g., 0,0 for top-left)\n"
                               "  STATE: State number to change to (0, 1, 2, etc.)\n"
                               "Example: --change-state CL123456789 Main 0,0 1",
                          metavar=("SERIAL", "PAGE", "COORDS", "STATE"))
    argparser.add_argument("--emulate-input", action="append", nargs=4,
                          help="Trigger a button action the same way a physical press would. Format: EVENT SERIAL PAGE COORDS\n"
                               "  EVENT: press or long-press\n"
                               "  SERIAL: Device serial number (e.g., CL123456789)\n"
                               "  PAGE: Page name (e.g., Main, Soundboard)\n"
                               "  COORDS: Position as x,y (e.g., 0,0 for top-left)\n"
                               "Example: --emulate-input press CL123456789 Main 0,0",
                          metavar=("EVENT", "SERIAL", "PAGE", "COORDS"))
    argparser.add_argument("--list-actions", action="append", nargs=3,
                          help="List the actions configured on a StreamDeck item. Format: PAGE COORDS STATE\n"
                               "  PAGE: Page name (e.g., Main, Soundboard)\n"
                               "  COORDS: Position as x,y (e.g., 0,0 for top-left)\n"
                               "  STATE: State number to inspect (0, 1, 2, etc.)\n"
                               "Example: --list-actions Main 0,0 0",
                          metavar=("PAGE", "COORDS", "STATE"))

    # Page management
    argparser.add_argument("--create-page", action="append", nargs=1, help="Create a new, empty page", metavar="NAME")
    argparser.add_argument("--delete-page", action="append", nargs=1, help="Delete a page", metavar="NAME")
    argparser.add_argument("--rename-page", action="append", nargs=2, help="Rename a page", metavar=("NAME", "NEW_NAME"))
    argparser.add_argument("--duplicate-page", action="append", nargs=2, help="Duplicate a page under a new name", metavar=("NAME", "NEW_NAME"))
    argparser.add_argument("--export-page", action="append", nargs=2, help="Export a single page (with its assets) to a .scpage file", metavar=("NAME", "DEST_PATH"))
    argparser.add_argument("--export-all", action="append", nargs=1, help="Export all pages (with their assets) to a .zip file, same as Page Manager's 'Export All'", metavar="DEST_PATH")

    # State management
    argparser.add_argument("--add-state", action="append", nargs=2, help="Add a new state to a StreamDeck item", metavar=("PAGE", "COORDS"))
    argparser.add_argument("--remove-state", action="append", nargs=3, help="Remove a state from a StreamDeck item", metavar=("PAGE", "COORDS", "STATE"))

    # Labels
    argparser.add_argument("--get-label", action="append", nargs=5,
                          help="Get a label property. PROPERTY: text, font-family, font-size, font-style, font-weight, color, outline-width, outline-color, align",
                          metavar=("PAGE", "COORDS", "STATE", "POSITION", "PROPERTY"))
    argparser.add_argument("--set-label", action="append", nargs=6,
                          help="Set a label property. PROPERTY: text, font-family, font-size, font-style, font-weight, color, outline-width, outline-color, align. "
                               "COLOR values use 'R,G,B' or 'R,G,B,A' (0-255)",
                          metavar=("PAGE", "COORDS", "STATE", "POSITION", "PROPERTY", "VALUE"))

    # Background
    argparser.add_argument("--get-background-color", action="append", nargs=3, help="Get the background color of a state", metavar=("PAGE", "COORDS", "STATE"))
    argparser.add_argument("--set-background-color", action="append", nargs=4,
                          help="Set the background color of a state. COLOR: 'R,G,B' or 'R,G,B,A' (0-255)",
                          metavar=("PAGE", "COORDS", "STATE", "COLOR"))

    # Icon / media
    argparser.add_argument("--get-icon", action="append", nargs=3, help="Get the icon (media path) of a state", metavar=("PAGE", "COORDS", "STATE"))
    argparser.add_argument("--set-icon", action="append", nargs=4,
                          help="Set the icon of a state from an image/gif/video file. The file is imported through the asset manager",
                          metavar=("PAGE", "COORDS", "STATE", "PATH"))
    argparser.add_argument("--get-icon-layout", action="append", nargs=4,
                          help="Get an icon layout property. PROPERTY: size, valign, halign, fill-mode",
                          metavar=("PAGE", "COORDS", "STATE", "PROPERTY"))
    argparser.add_argument("--set-icon-layout", action="append", nargs=5,
                          help="Set an icon layout property. PROPERTY: size, valign, halign, fill-mode",
                          metavar=("PAGE", "COORDS", "STATE", "PROPERTY", "VALUE"))

    # Brightness
    argparser.add_argument("--get-brightness", action="append", nargs=1, help="Get the brightness of a device (0-100)", metavar="SERIAL")
    argparser.add_argument("--set-brightness", action="append", nargs=2, help="Set the brightness of a device (0-100)", metavar=("SERIAL", "VALUE"))

    # Screensaver / sleep
    argparser.add_argument("--sleep", action="append", nargs=1, help="Put a device to sleep (show the screensaver now). Requires a running instance", metavar="SERIAL")
    argparser.add_argument("--wake", action="append", nargs=1, help="Wake a device from sleep. Requires a running instance", metavar="SERIAL")

    argparser.add_argument("app_args", nargs="*")

    return argparser


# ── Validation ───────────────────────────────────────────────────────

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


def validate_emulate_input_args(args):
    """
    Validate CLI arguments for --emulate-input
    Returns (is_valid, error_message)
    """
    if not args.emulate_input:
        return True, None

    for i, (event, serial_number, page_name, coords) in enumerate(args.emulate_input):
        if event not in VALID_EMULATE_INPUT_EVENTS:
            return False, f"Invalid event in argument {i+1}: '{event}'. Must be one of: {', '.join(VALID_EMULATE_INPUT_EVENTS)}"

        if not serial_number or not isinstance(serial_number, str):
            return False, f"Invalid serial number in argument {i+1}: '{serial_number}'"

        if not page_name or not isinstance(page_name, str):
            return False, f"Invalid page name in argument {i+1}: '{page_name}'"

        if not coords or not isinstance(coords, str) or ',' not in coords:
            return False, f"Invalid coordinate format in argument {i+1}: '{coords}'. Expected format: 'x,y' (e.g., '0,0')"

        try:
            x, y = map(int, coords.split(','))
            if x < 0 or y < 0:
                return False, f"Coordinates must be non-negative in argument {i+1}: '{coords}'"
            if x > MAX_REASONABLE_X or y > MAX_REASONABLE_Y:
                return False, f"Coordinates seem too large in argument {i+1}: '{coords}'. Most StreamDecks have coordinates 0-4"
        except ValueError:
            return False, f"Invalid coordinate format in argument {i+1}: '{coords}'. Expected integers like '0,0'"

    return True, None


def print_state_change_usage() -> None:
    print("\nUsage examples:", file=sys.stderr)
    print("  --change-state CL123456789 Main 0,0 1", file=sys.stderr)
    print("  --change-state CL123456789 Soundboard 2,1 0", file=sys.stderr)
    print("\nParameters:", file=sys.stderr)
    print("  SERIAL_NUMBER: Device serial (e.g., CL123456789)", file=sys.stderr)
    print("  PAGE_NAME: Page name (e.g., Main, Soundboard)", file=sys.stderr)
    print("  COORDINATES: Position as x,y (e.g., 0,0 for top-left)", file=sys.stderr)
    print("  STATE_NUMBER: State to change to (e.g., 0, 1, 2)", file=sys.stderr)


def print_emulate_input_usage() -> None:
    print("\nUsage examples:", file=sys.stderr)
    print("  --emulate-input press CL123456789 Main 0,0", file=sys.stderr)
    print("  --emulate-input long-press CL123456789 Soundboard 2,1", file=sys.stderr)
    print("\nParameters:", file=sys.stderr)
    print(f"  EVENT: {' or '.join(VALID_EMULATE_INPUT_EVENTS)}", file=sys.stderr)
    print("  SERIAL_NUMBER: Device serial (e.g., CL123456789)", file=sys.stderr)
    print("  PAGE_NAME: Page name (e.g., Main, Soundboard)", file=sys.stderr)
    print("  COORDINATES: Position as x,y (e.g., 0,0 for top-left)", file=sys.stderr)


# ── DBus ─────────────────────────────────────────────────────────────

def get_dbus_api():
    """
    One-shot blocking connection to a running instance's rich API
    (com.core447.StreamController, see src/api.py), or None if no instance
    answers. Never attached to a mainloop - see tests/test_dbus_mainloop.py.
    """
    if sys.platform == "darwin":
        return None
    try:
        import dbus
        session_bus = dbus.SessionBus()
        obj = session_bus.get_object(DBUS_NAME, DBUS_PATH)
        return dbus.Interface(obj, DBUS_NAME)
    except Exception:
        # No session bus, no instance, or a malformed bus address - the caller
        # falls back to doing the work itself
        return None


# ── Fast path ────────────────────────────────────────────────────────

# Every flag that maps onto a method of the DBus API. Matched against argv
# before anything is parsed or imported, so a normal app start pays nothing
# for this.
FAST_PATH_FLAGS = frozenset((
    "--change-page", "--change-state", "--emulate-input",
    "--create-page", "--delete-page", "--rename-page", "--duplicate-page",
    "--export-page", "--export-all",
    "--add-state", "--remove-state",
    "--get-label", "--set-label",
    "--get-background-color", "--set-background-color",
    "--get-icon", "--set-icon", "--get-icon-layout", "--set-icon-layout",
    "--get-brightness", "--set-brightness",
    "--sleep", "--wake",
))


def _has_fast_path_flag(argv) -> bool:
    return any(arg.split("=", 1)[0] in FAST_PATH_FLAGS for arg in argv)


def _error_message(e) -> str:
    """The human readable half of a DBusException raised by src/api.py.

    api.py raises dasbus' DBusError(error_name, message), and dasbus puts
    str() of that whole tuple on the wire as the message, so what arrives here
    is `('com.core447...PageNotFound', "Page 'x' not found")`. Unwrap it so the
    CLI prints the message the API actually wrote."""
    message = e.get_dbus_message()
    if message.startswith("(") and message.endswith(")"):
        try:
            import ast
            parts = ast.literal_eval(message)
            if isinstance(parts, tuple) and parts:
                return str(parts[-1])
        except (ValueError, SyntaxError):
            pass
    return message


def print_get_results(results: list[dict], as_json: bool) -> None:
    """Shared by the fast path and main.py's on-disk reads so both print the
    same thing. `value` is always a string, as the DBus API returns it."""
    if as_json:
        print(json.dumps(results, indent=2))
        return
    for entry in results:
        label = f"{entry.get('page')} {entry.get('coords')} state={entry.get('state')}"
        if "position" in entry:
            label += f" {entry['position']}.{entry['property']}"
        elif "property" in entry:
            label += f" {entry['property']}"
        if "error" in entry:
            print(f"{label}: Error: {entry['error']}")
        else:
            print(f"{label}: {entry['value']}")


def run_against_running_instance() -> bool:
    """Handle the command by calling a running instance over DBus.

    Returns True if the command was fully handled (the caller should exit),
    False if main.py has to take over."""
    argv = sys.argv[1:]
    if sys.platform == "darwin" or not _has_fast_path_flag(argv):
        return False

    if "--close-running" in argv:
        # The request is meant for the instance that is about to replace the
        # running one, so main.py buffers it and applies it after startup
        return False

    api = get_dbus_api()
    if api is None:
        return False

    args = build_argparser().parse_args()

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

    if _dispatch(args, api):
        sys.exit(1)
    return True


def _dispatch(args, api) -> bool:
    """Runs every requested command against `api`. Returns True if any failed."""
    import dbus

    had_error = False

    def call(fn):
        nonlocal had_error
        try:
            return fn()
        except dbus.exceptions.DBusException as e:
            print(f"Error: {_error_message(e)}", file=sys.stderr)
            had_error = True
            return None

    def read(entry: dict, fn, results: list[dict]) -> None:
        """A read reports its failure inside the result row rather than on
        stderr, so --json output still has one row per requested read - same
        shape main.py produces when it reads the page json itself."""
        nonlocal had_error
        try:
            entry["value"] = str(fn())
        except dbus.exceptions.DBusException as e:
            entry["error"] = _error_message(e)
            had_error = True
        results.append(entry)

    # ── Runtime page / state / input control ────────────────────────

    for serial, page_name in args.change_page or []:
        call(lambda serial=serial, page_name=page_name: api.ChangePage(serial, page_name))

    for serial, page_name, coords, state in args.change_state or []:
        call(lambda serial=serial, page_name=page_name, coords=coords, state=state:
             api.ChangeState(serial, page_name, coords, int(state)))

    for event, serial, page_name, coords in args.emulate_input or []:
        call(lambda event=event, serial=serial, page_name=page_name, coords=coords:
             api.EmulateInput(event, serial, page_name, coords))

    # ── Page management ─────────────────────────────────────────────

    for (name,) in args.create_page or []:
        call(lambda name=name: api.AddPage(name, "{}"))

    for (name,) in args.delete_page or []:
        call(lambda name=name: api.RemovePage(name))

    for name, new_name in args.rename_page or []:
        call(lambda name=name, new_name=new_name: api.RenamePage(name, new_name))

    for name, new_name in args.duplicate_page or []:
        call(lambda name=name, new_name=new_name: api.DuplicatePage(name, new_name))

    for name, dest_path in args.export_page or []:
        dest_path = os.path.abspath(dest_path)
        if call(lambda name=name, dest_path=dest_path: api.ExportPage(name, dest_path)) is not None:
            print(f"Exported '{name}' to {dest_path}")

    for (dest_path,) in args.export_all or []:
        dest_path = os.path.abspath(dest_path)
        if call(lambda dest_path=dest_path: api.ExportAll(dest_path)) is not None:
            print(f"Exported all pages to {dest_path}")

    # ── States ───────────────────────────────────────────────────────

    for name, coords in args.add_state or []:
        new_index = call(lambda name=name, coords=coords: api.AddState(name, coords))
        if new_index is not None:
            print(f"Added state {new_index} to {name} {coords}")

    for name, coords, state in args.remove_state or []:
        call(lambda name=name, coords=coords, state=state: api.RemoveState(name, coords, int(state)))

    # ── Labels ───────────────────────────────────────────────────────

    results = []
    for name, coords, state, position, prop in args.get_label or []:
        read({"page": name, "coords": coords, "state": state, "position": position, "property": prop},
             lambda name=name, coords=coords, state=state, position=position, prop=prop:
             api.GetLabel(name, coords, int(state), position, prop), results)
    if results:
        print_get_results(results, args.json)

    for name, coords, state, position, prop, value in args.set_label or []:
        call(lambda name=name, coords=coords, state=state, position=position, prop=prop, value=value:
             api.SetLabel(name, coords, int(state), position, prop, value))

    # ── Background color ────────────────────────────────────────────

    results = []
    for name, coords, state in args.get_background_color or []:
        read({"page": name, "coords": coords, "state": state},
             lambda name=name, coords=coords, state=state: api.GetBackgroundColor(name, coords, int(state)), results)
    if results:
        print_get_results(results, args.json)

    for name, coords, state, color in args.set_background_color or []:
        call(lambda name=name, coords=coords, state=state, color=color:
             api.SetBackgroundColor(name, coords, int(state), color))

    # ── Icon / media ─────────────────────────────────────────────────

    results = []
    for name, coords, state in args.get_icon or []:
        read({"page": name, "coords": coords, "state": state},
             lambda name=name, coords=coords, state=state: api.GetIcon(name, coords, int(state)), results)
    if results:
        print_get_results(results, args.json)

    for name, coords, state, path in args.set_icon or []:
        path = os.path.abspath(path)
        internal_path = call(lambda name=name, coords=coords, state=state, path=path:
                             api.SetIcon(name, coords, int(state), path))
        if internal_path is not None:
            print(f"Set icon for {name} {coords} state {state}: {internal_path}")

    results = []
    for name, coords, state, prop in args.get_icon_layout or []:
        read({"page": name, "coords": coords, "state": state, "property": prop},
             lambda name=name, coords=coords, state=state, prop=prop:
             api.GetIconLayout(name, coords, int(state), prop), results)
    if results:
        print_get_results(results, args.json)

    for name, coords, state, prop, value in args.set_icon_layout or []:
        call(lambda name=name, coords=coords, state=state, prop=prop, value=value:
             api.SetIconLayout(name, coords, int(state), prop, value))

    # ── Brightness ───────────────────────────────────────────────────

    for (serial,) in args.get_brightness or []:
        value = call(lambda serial=serial: api.GetBrightness(serial))
        if value is not None:
            print(int(value))

    for serial, value in args.set_brightness or []:
        try:
            value_int = int(value)
        except ValueError:
            print(f"Error: Invalid brightness '{value}'. Must be an integer 0-100", file=sys.stderr)
            had_error = True
            continue
        call(lambda serial=serial, value_int=value_int: api.SetBrightness(serial, value_int))

    # ── Sleep / wake ─────────────────────────────────────────────────

    for (serial,) in args.sleep or []:
        call(lambda serial=serial: api.Sleep(serial))

    for (serial,) in args.wake or []:
        call(lambda serial=serial: api.Wake(serial))

    return had_error
