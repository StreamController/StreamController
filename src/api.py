"""
StreamController DBus API

Provides a DBus interface at com.core447.StreamController for external
tools to query and control StreamController.

Top-level object: /com/core447/StreamController
  - Controllers property (list of serial numbers)
  - Pages property, AddPage, RemovePage
  - NotifyForegroundWindow, IconPacks property, GetIconNames
  - ForegroundWindow property (WindowInfo struct)

Per-controller objects: /com/core447/StreamController/controllers/<serial>
  - SetActivePage
  - ActivePageName property
"""

import functools
import json
import os
import re
from collections import namedtuple
from typing import Tuple
from src.Signals import Signals
from loguru import logger as log

from dasbus.server.interface import dbus_interface
from dasbus.connection import SessionMessageBus
from dasbus.typing import Str, Int, List
from dasbus.error import DBusError
from gi.repository import GLib, Gio

import globals as gl
from src.backend.DeckManagement.HelperMethods import recursive_hasattr
from src.backend.PageManagement import HeadlessPageOps as ops

ERR = "com.core447.StreamController.Error."


def _wrap_dbus_errors(func):
    """Turns HeadlessPageOps/lookup failures into proper DBusErrors instead of
    the log-and-swallow pattern the older methods on this class use - callers
    scripting against this API need a real error, not a silent no-op."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except DBusError:
            raise
        except ops.HeadlessOpError as e:
            raise DBusError(ERR + "InvalidArgument", str(e))
        except Exception as e:
            log.error(f"DBus API: {func.__name__} error: {e}")
            raise DBusError(ERR + "Failed", str(e))
    return wrapper


def _refresh_sidebar():
    """Nudges the Sidebar to reload whatever key is currently selected, in case
    it's the one that was just edited. The Sidebar's editors (LabelEditor,
    BackgroundEditor, IconSelector, ...) all re-read live data on every call,
    but nothing tells them *when* to - Page.set_label_text() & co only push a
    redraw to the physical/rendered key (Page.update_input()), never to the
    Sidebar widgets showing the same value. Sidebar.update() is already used
    this exact way elsewhere (e.g. DeckController.ControllerInput.reload_sidebar())
    and is a cheap no-op-ish re-render when the edited key isn't the selected one.
    It also picks up added/removed states via the StateSwitcher."""
    if recursive_hasattr(gl, "app.main_win.sidebar"):
        GLib.idle_add(gl.app.main_win.sidebar.update)


def _refresh_deck_settings(serial: str) -> None:
    """Reloads the deck settings page of one deck so a value changed over DBus
    (brightness) is reflected in the slider showing it, not just on the deck."""
    if not recursive_hasattr(gl, "app.main_win.leftArea.deck_stack"):
        return

    child = gl.app.main_win.leftArea.deck_stack.get_child_by_name(serial)
    if child is None:
        return
    GLib.idle_add(child.deck_settings.settings_group.brightness.load_default)


def _live_pages(page_path: str) -> list:
    """The Page objects for this json that a deck is currently showing.

    Those are the only ones an edit has to be pushed to - a page that isn't on
    any deck has nothing live to update. Matched by abspath because the same
    page can reach us in different spellings (a CLI-relative path vs. the
    absolute one stored in the default-pages settings)."""
    if gl.deck_manager is None:
        return []

    abs_target = os.path.abspath(page_path)
    pages = []
    for controller in gl.deck_manager.deck_controller:
        page = controller.active_page
        if page is not None and os.path.abspath(page.json_path) == abs_target:
            pages.append(page)
    return pages


def _reload_input(page_path: str, identifier) -> None:
    """Push a just-saved page edit onto every deck showing that page.

    Writing the json is not enough: a running instance keeps the rendered key
    in memory and only rebuilds it from the page dict when the input is
    (re)loaded. Page's own set_* methods push a few properties into the live
    managers, but not all of them - Page.set_media_path() in particular assigns
    to ImageLayout.path, a field that does not exist and that nothing renders,
    so an icon set over DBus only appeared after a restart. Reloading the whole
    input from the page dict is what the UI itself does after an icon change
    (IconSelector.set_media_callback) and covers media, labels, background,
    layout and the number of states in one go."""
    for page in _live_pages(page_path):
        page.update_dict()
        page.deck_controller.load_input_from_identifier(identifier, page)
    _refresh_sidebar()

WindowInfo = namedtuple("WindowInfo", ["name", "wm_class"])

DBUS_OBJECT_PATH = "/com/core447/StreamController"
CONTROLLER_BASE_PATH = DBUS_OBJECT_PATH + "/controllers"
TOP_IFACE = "com.core447.StreamController"
CTRL_IFACE = "com.core447.StreamController.Controller"
PROPS_IFACE = "org.freedesktop.DBus.Properties"


def _emit_properties_changed(object_path: str, interface: str,
                             changed: dict, invalidated: list[str] | None = None):
    """Emit org.freedesktop.DBus.Properties.PropertiesChanged on the bus."""
    if _bus is None:
        return
    try:
        connection = _bus.connection
        body = GLib.Variant("(sa{sv}as)", (
            interface,
            changed,
            invalidated or [],
        ))
        connection.emit_signal(
            None,           # destination (broadcast)
            object_path,
            PROPS_IFACE,
            "PropertiesChanged",
            body,
        )
    except Exception as e:
        log.debug(f"DBus API: Failed to emit PropertiesChanged: {e}")


def _serial_to_dbus_path(serial: str) -> str:
    """Convert a serial number to a valid DBus object path component."""
    # DBus paths only allow [A-Za-z0-9_], so replace anything else with _
    return re.sub(r"[^A-Za-z0-9_]", "_", serial)


# ─────────────────────────────────────────────────────────────────────
# Per-controller API (published at .../controllers/<serial>)
# ─────────────────────────────────────────────────────────────────────

@dbus_interface("com.core447.StreamController.Controller")
class ControllerInstanceAPI:
    """DBus interface for a single StreamDeck controller."""

    def __init__(self, controller):
        self._controller = controller
        self._active_page_name: str = ""
        self._object_path: str = ""  # set by _publish_controller

    # ── Methods ──────────────────────────────────────────────────────

    def SetActivePage(self, name: Str) -> None:
        """Set the active page on this controller."""
        serial = self._controller.serial_number()
        log.info(f"DBus API [{serial}]: SetActivePage called – name={name!r}")
        try:
            if gl.page_manager is not None:
                page_path = gl.page_manager.find_matching_page_path(name)
                if page_path is None:
                    log.warning(f"DBus API [{serial}]: SetActivePage – page not found: {name}")
                    return
                page = gl.page_manager.get_page(page_path, self._controller)
                self._controller.load_page(page)
                self._active_page_name = name
        except Exception as e:
            log.error(f"DBus API [{serial}]: SetActivePage error: {e}")

    # ── Properties ───────────────────────────────────────────────────

    @property
    def ActivePageName(self) -> Str:
        """The name of the currently active page on this controller."""
        return self._active_page_name

    @ActivePageName.setter
    def ActivePageName(self, value: Str):
        self._active_page_name = value
        log.debug(f"DBus API [{self._controller.serial_number()}]: ActivePageName changed to {value!r}")
        if self._object_path:
            _emit_properties_changed(
                self._object_path, CTRL_IFACE,
                {"ActivePageName": GLib.Variant("s", value)},
            )


# ─────────────────────────────────────────────────────────────────────
# Top-level API (published at /com/core447/StreamController)
# ─────────────────────────────────────────────────────────────────────

@dbus_interface("com.core447.StreamController")
class StreamControllerAPI:
    """DBus interface for StreamController (top-level)."""

    def __init__(self):
        self._foreground_window: WindowInfo = WindowInfo("", "")

    # ── Methods ──────────────────────────────────────────────────────

    @property
    def Pages(self) -> List[Str]:
        """Return a list of page names."""
        log.info("DBus API: Pages read")
        try:
            if gl.page_manager is not None:
                return gl.page_manager.get_page_names()
        except Exception as e:
            log.error(f"DBus API: Pages error: {e}")
        return []

    def AddPage(self, name: Str, json_contents: Str) -> None:
        """Add a new page with the given name and JSON contents."""
        log.info(f"DBus API: AddPage called – name={name!r}")
        try:
            page_dict = json.loads(json_contents) if json_contents else {}
            if gl.page_manager is not None:
                path = gl.page_manager.add_page(name, page_dict)
                gl.page_manager.update_dict_of_pages_with_path(path)
                gl.page_manager.reload_pages_with_path(path)
                gl.signal_manager.trigger_signal(Signals.PageAdd, path)
        except FileExistsError as e:
            raise DBusError(
                "com.core447.StreamController.Error.PageExists",
                f"Page '{name}' already exists"
            )
        except json.JSONDecodeError as e:
            log.error(f"DBus API: AddPage – invalid JSON: {e}")
        except Exception as e:
            log.error(f"DBus API: AddPage error: {e}")

    def RemovePage(self, name: Str) -> None:
        """Remove the page with the given name."""
        log.info(f"DBus API: RemovePage called – name={name!r}")
        try:
            if gl.page_manager is not None:
                page_path = os.path.join(gl.page_manager.PAGE_PATH, f"{name}.json")
                if os.path.exists(page_path):
                    gl.page_manager.remove_page(page_path)
                    gl.signal_manager.trigger_signal(Signals.PageDelete, page_path)
                else:
                    log.warning(f"DBus API: RemovePage – page not found: {name}")
        except Exception as e:
            log.error(f"DBus API: RemovePage error: {e}")

    def NotifyForegroundWindow(self, name: Str, wm_class: Str) -> None:
        """
        Notify StreamController of the current foreground window.
        Useful for testing/development without kdotool.
        """
        win = WindowInfo(name, wm_class)
        log.info(f"DBus API: NotifyForegroundWindow called – {win!r}")
        try:
            if gl.window_grabber is not None:
                from src.backend.WindowGrabber.Window import Window
                window = Window(wm_class=win.wm_class, title=win.name)
                gl.window_grabber.on_active_window_changed(window)
        except Exception as e:
            log.error(f"DBus API: NotifyForegroundWindow error: {e}")

    @property
    def IconPacks(self) -> List[Str]:
        """Return a list of icon pack IDs."""
        log.info("DBus API: IconPacks read")
        try:
            if gl.icon_pack_manager is not None:
                packs = gl.icon_pack_manager.get_icon_packs()
                return list(packs.keys())
        except Exception as e:
            log.error(f"DBus API: IconPacks error: {e}")
        return []

    def GetIconNames(self, icon_pack_id: Str) -> List[Str]:
        """Return a list of all icon names in the given icon pack."""
        log.info(f"DBus API: GetIconNames called – icon_pack_id={icon_pack_id!r}")
        try:
            if gl.icon_pack_manager is not None:
                packs = gl.icon_pack_manager.get_icon_packs()
                pack = packs.get(icon_pack_id)
                if pack is None:
                    log.warning(f"DBus API: GetIconNames – pack not found: {icon_pack_id}")
                    return []
                icons = pack.get_icons()
                return [icon.name for icon in icons]
        except Exception as e:
            log.error(f"DBus API: GetIconNames error: {e}")
        return []

    # ── Internal helpers ─────────────────────────────────────────────

    def _get_controller_by_serial(self, serial: str):
        if gl.deck_manager is None:
            return None
        for controller in gl.deck_manager.deck_controller:
            if controller.serial_number() == serial:
                return controller
        return None

    def _require_controller(self, serial: str):
        controller = self._get_controller_by_serial(serial)
        if controller is None:
            raise DBusError(ERR + "ControllerNotFound", f"No connected controller with serial '{serial}'")
        return controller

    def _get_page_path(self, name: str) -> str:
        if gl.page_manager is None:
            raise DBusError(ERR + "NotReady", "PageManager not initialized")
        page_path = gl.page_manager.find_matching_page_path(name)
        if page_path is None:
            raise DBusError(ERR + "PageNotFound", f"Page '{name}' not found")
        return page_path

    def _get_page_for_editing(self, name: str):
        """(page_path, page) for the given page name.

        `page` is the live Page object if the page is currently shown on a
        deck, and None otherwise - in which case callers go through
        HeadlessPageOps and edit the json directly, exactly like the CLI does
        when no instance is running at all. Editing a page that isn't on any
        deck must not go through a Page object: Page's set_* methods write
        through to every ControllerInput with a matching identifier regardless
        of which page that deck is actually showing, so they would corrupt the
        in-memory state of an unrelated key."""
        page_path = self._get_page_path(name)
        pages = _live_pages(page_path)
        return page_path, (pages[0] if pages else None)

    @staticmethod
    def _validate_label_args(position: str, property: str) -> None:
        if position not in ops.LABEL_POSITIONS:
            raise DBusError(ERR + "InvalidArgument", f"Invalid label position '{position}'. Must be one of: {', '.join(ops.LABEL_POSITIONS)}")
        if property not in ops.LABEL_PROPERTIES:
            raise DBusError(ERR + "InvalidArgument", f"Invalid label property '{property}'. Must be one of: {', '.join(ops.LABEL_PROPERTIES)}")

    @staticmethod
    def _validate_media_args(property: str) -> None:
        if property not in ops.MEDIA_PROPERTIES:
            raise DBusError(ERR + "InvalidArgument", f"Invalid media property '{property}'. Must be one of: {', '.join(ops.MEDIA_PROPERTIES)}")

    # ── Page management ──────────────────────────────────────────────

    @_wrap_dbus_errors
    def RenamePage(self, name: Str, new_name: Str) -> None:
        log.info(f"DBus API: RenamePage called – {name!r} -> {new_name!r}")
        page_path = self._get_page_path(name)
        new_path = os.path.join(gl.page_manager.PAGE_PATH, f"{new_name}.json")
        if os.path.exists(new_path):
            raise DBusError(ERR + "PageExists", f"Page '{new_name}' already exists")
        gl.page_manager.move_page(page_path, new_path)
        gl.signal_manager.trigger_signal(Signals.PageRename, page_path, new_path)

        # move_page() rewrites json_path on the loaded Page objects, but the
        # ActivePageName property is only pushed from load_page() - without this
        # it would keep reporting the old name until the next page change
        for page in _live_pages(new_path):
            notify_active_page_changed(page.deck_controller.serial_number(), page.get_name())

    @_wrap_dbus_errors
    def DuplicatePage(self, name: Str, new_name: Str) -> None:
        log.info(f"DBus API: DuplicatePage called – {name!r} -> {new_name!r}")
        page_path = self._get_page_path(name)
        data = gl.page_manager.get_page_data(page_path)
        try:
            new_path = gl.page_manager.add_page(new_name, data)
        except FileExistsError:
            raise DBusError(ERR + "PageExists", f"Page '{new_name}' already exists")
        gl.page_manager.update_dict_of_pages_with_path(new_path)
        gl.signal_manager.trigger_signal(Signals.PageAdd, new_path)

    @_wrap_dbus_errors
    def ExportPage(self, name: Str, dest_path: Str) -> None:
        log.info(f"DBus API: ExportPage called – {name!r} -> {dest_path!r}")
        from src.backend.PageManagement import PageBundle
        page_path = self._get_page_path(name)
        PageBundle.export_page(page_path, dest_path)

    @_wrap_dbus_errors
    def ExportAll(self, dest_path: Str) -> None:
        log.info(f"DBus API: ExportAll called – {dest_path!r}")
        from src.backend.PageManagement import PageBundle
        if dest_path.endswith(".json"):
            pages = {os.path.basename(p): gl.page_manager.get_page_data(p) for p in gl.page_manager.get_pages(add_custom_pages=False)}
            from src.backend.Utils.AtomicSaveUtils import atomic_save_json
            atomic_save_json(dest_path, pages)
        else:
            PageBundle.export_pages(gl.page_manager.get_pages(add_custom_pages=False), dest_path)

    # ── States ───────────────────────────────────────────────────────

    @_wrap_dbus_errors
    def AddState(self, name: Str, coords: Str) -> Int:
        log.info(f"DBus API: AddState called – {name!r} {coords!r}")
        page_path = self._get_page_path(name)
        new_index = ops.add_state(page_path, coords)
        _reload_input(page_path, ops.identifier_from_coords(coords))
        return new_index

    @_wrap_dbus_errors
    def RemoveState(self, name: Str, coords: Str, state: Int) -> None:
        log.info(f"DBus API: RemoveState called – {name!r} {coords!r} state={state}")
        page_path = self._get_page_path(name)
        ops.remove_state(page_path, coords, state)
        _reload_input(page_path, ops.identifier_from_coords(coords))

    # ── Labels ───────────────────────────────────────────────────────

    @_wrap_dbus_errors
    def GetLabel(self, name: Str, coords: Str, state: Int, position: Str, property: Str) -> Str:
        self._validate_label_args(position, property)
        page_path, page = self._get_page_for_editing(name)
        if page is None:
            return ops.format_value(ops.get_label(page_path, coords, state, position, property))
        getter = getattr(page, f"get_label_{ops.LABEL_METHOD[property]}")
        return ops.format_value(getter(ops.identifier_from_coords(coords), state, position))

    @_wrap_dbus_errors
    def SetLabel(self, name: Str, coords: Str, state: Int, position: Str, property: Str, value: Str) -> None:
        log.info(f"DBus API: SetLabel called – {name!r} {coords!r} state={state} {position}.{property}={value!r}")
        self._validate_label_args(position, property)
        page_path, page = self._get_page_for_editing(name)
        if page is None:
            ops.set_label(page_path, coords, state, position, property, value)
            return
        identifier = ops.identifier_from_coords(coords)
        setter = getattr(page, f"set_label_{ops.LABEL_METHOD[property]}")
        setter(identifier, state, position, ops.coerce_label_value(property, value))
        _refresh_sidebar()

    # ── Background color ─────────────────────────────────────────────

    @_wrap_dbus_errors
    def GetBackgroundColor(self, name: Str, coords: Str, state: Int) -> Str:
        page_path, page = self._get_page_for_editing(name)
        if page is None:
            return ops.format_value(ops.get_background_color(page_path, coords, state))
        return ops.format_value(page.get_background_color(ops.identifier_from_coords(coords), state))

    @_wrap_dbus_errors
    def SetBackgroundColor(self, name: Str, coords: Str, state: Int, color: Str) -> None:
        log.info(f"DBus API: SetBackgroundColor called – {name!r} {coords!r} state={state} color={color!r}")
        page_path, page = self._get_page_for_editing(name)
        if page is None:
            ops.set_background_color(page_path, coords, state, color)
            return
        page.set_background_color(ops.identifier_from_coords(coords), state, ops.parse_color(color))
        _refresh_sidebar()

    # ── Icon / media ─────────────────────────────────────────────────

    @_wrap_dbus_errors
    def GetIcon(self, name: Str, coords: Str, state: Int) -> Str:
        page_path, page = self._get_page_for_editing(name)
        if page is None:
            return ops.format_value(ops.get_media(page_path, coords, state, "path"))
        return ops.format_value(page.get_media_path(ops.identifier_from_coords(coords), state))

    @_wrap_dbus_errors
    def SetIcon(self, name: Str, coords: Str, state: Int, path: Str) -> Str:
        log.info(f"DBus API: SetIcon called – {name!r} {coords!r} state={state} path={path!r}")
        if not os.path.isfile(path):
            raise DBusError(ERR + "InvalidArgument", f"File not found: {path}")
        ops.bootstrap_asset_manager()
        asset_id = gl.asset_manager_backend.add(path)
        if asset_id is None:
            raise DBusError(ERR + "InvalidArgument", f"'{path}' could not be added as an asset (unsupported/undecodable file)")
        internal_path = gl.asset_manager_backend.get_by_id(asset_id)["internal-path"]

        page_path, page = self._get_page_for_editing(name)
        identifier = ops.identifier_from_coords(coords)
        if page is None:
            ops.set_media(page_path, coords, state, "path", internal_path)
            return internal_path

        # update=False: the media itself is only picked up by the reload below -
        # set_media_path() writes the json but has nothing to hand the new image to
        page.set_media_path(identifier, state, internal_path, update=False)
        _reload_input(page_path, identifier)
        return internal_path

    @_wrap_dbus_errors
    def GetIconLayout(self, name: Str, coords: Str, state: Int, property: Str) -> Str:
        self._validate_media_args(property)
        page_path, page = self._get_page_for_editing(name)
        if page is None:
            return ops.format_value(ops.get_media(page_path, coords, state, property))
        getter = getattr(page, f"get_media_{ops.MEDIA_METHOD[property]}")
        return ops.format_value(getter(ops.identifier_from_coords(coords), state))

    @_wrap_dbus_errors
    def SetIconLayout(self, name: Str, coords: Str, state: Int, property: Str, value: Str) -> None:
        log.info(f"DBus API: SetIconLayout called – {name!r} {coords!r} state={state} {property}={value!r}")
        self._validate_media_args(property)
        page_path, page = self._get_page_for_editing(name)
        if page is None:
            ops.set_media(page_path, coords, state, property, value)
            return
        identifier = ops.identifier_from_coords(coords)
        if property == "path":
            # Not a layout property - same story as SetIcon above
            page.set_media_path(identifier, state, value, update=False)
            _reload_input(page_path, identifier)
            return
        setter = getattr(page, f"set_media_{ops.MEDIA_METHOD[property]}")
        setter(identifier, state, ops.coerce_media_value(property, value))
        _refresh_sidebar()

    # ── Deck state ───────────────────────────────────────────────────

    @_wrap_dbus_errors
    def GetBrightness(self, serial: Str) -> Int:
        controller = self._require_controller(serial)
        return int(controller.brightness)

    @_wrap_dbus_errors
    def SetBrightness(self, serial: Str, value: Int) -> None:
        log.info(f"DBus API: SetBrightness called – {serial!r} value={value}")
        controller = self._require_controller(serial)
        settings = gl.settings_manager.get_deck_settings(serial)
        settings.setdefault("brightness", {})["value"] = value
        gl.settings_manager.save_deck_settings(serial, settings)
        controller.set_brightness(value)
        _refresh_deck_settings(serial)

    @_wrap_dbus_errors
    def Sleep(self, serial: Str) -> None:
        log.info(f"DBus API: Sleep called – {serial!r}")
        controller = self._require_controller(serial)
        if not controller.screen_saver.showing:
            controller.screen_saver.show()

    @_wrap_dbus_errors
    def Wake(self, serial: Str) -> None:
        log.info(f"DBus API: Wake called – {serial!r}")
        controller = self._require_controller(serial)
        if controller.screen_saver.showing:
            controller.screen_saver.hide()

    # ── Runtime page/state/input control ────────────────────────────
    # Consolidated from src/app.py's org.gtk.Actions handlers (change_page,
    # change_state, trigger_action), which duplicated this exact logic.

    @_wrap_dbus_errors
    def ChangePage(self, serial: Str, page_name: Str) -> None:
        """page_name can be either the name or the path of the page."""
        controller = self._require_controller(serial)
        page_path = self._get_page_path(page_name)
        if controller.active_page is not None and os.path.abspath(page_path) == os.path.abspath(controller.active_page.json_path):
            return
        page = gl.page_manager.get_page(page_path, controller)
        controller.load_page(page)

    @_wrap_dbus_errors
    def ChangeState(self, serial: Str, page_name: Str, coords: Str, state: Int) -> None:
        controller = self._require_controller(serial)
        page_path = self._get_page_path(page_name)

        if controller.active_page is None or os.path.abspath(page_path) != os.path.abspath(controller.active_page.json_path):
            page = gl.page_manager.get_page(page_path, controller)
            controller.load_page(page)

        identifier = ops.identifier_from_coords(coords)
        rows, cols = controller.deck.key_layout()
        x, y = identifier.coords
        if x < 0 or x >= cols or y < 0 or y >= rows:
            raise DBusError(ERR + "InvalidArgument", f"Coordinates ({x},{y}) are out of bounds. Valid range: x=0-{cols-1}, y=0-{rows-1}")

        c_input = controller.get_input(identifier)
        if c_input is None:
            raise DBusError(ERR + "InvalidArgument", f"Could not find input at coordinates ({x},{y})")
        if state < 0 or state >= len(c_input.states):
            raise DBusError(ERR + "InvalidArgument", f"Position ({x},{y}) has {len(c_input.states)} state(s) (0-{len(c_input.states)-1}). Requested state {state} does not exist")

        c_input.set_state(state)

    @_wrap_dbus_errors
    def EmulateInput(self, event: Str, serial: Str, page_name: Str, coords: Str) -> None:
        """Simulates a key press/long-press, triggering the same actions a physical press would."""
        controller = self._require_controller(serial)
        page_path = self._get_page_path(page_name)

        if controller.active_page is None or os.path.abspath(page_path) != os.path.abspath(controller.active_page.json_path):
            page = gl.page_manager.get_page(page_path, controller)
            controller.load_page(page)

        success, message = controller.trigger_action(coords, event)
        if not success:
            raise DBusError(ERR + "InvalidArgument", message)

    # ── Properties ───────────────────────────────────────────────────

    @property
    def DataPath(self) -> Str:
        """The base path where StreamController stores its data (pages, icons, etc). 
        (This is necessary for clients to compose valid JSON page files)"""
        return gl.DATA_PATH
    
    @property
    def Controllers(self) -> List[Str]:
        """Serial numbers of all connected controllers."""
        try:
            if gl.deck_manager is not None:
                return [c.serial_number() for c in gl.deck_manager.deck_controller]
        except Exception as e:
            log.error(f"DBus API: Controllers error: {e}")
        return []

    @property
    def ForegroundWindow(self) -> Tuple[Str, Str]:
        """The current foreground window as (name, wm_class)."""
        return (self._foreground_window.name, self._foreground_window.wm_class)

    @ForegroundWindow.setter
    def ForegroundWindow(self, value: Tuple[Str, Str]):
        self._foreground_window = WindowInfo(*value)
        log.debug(f"DBus API: ForegroundWindow changed to {self._foreground_window!r}")
        _emit_properties_changed(
            DBUS_OBJECT_PATH, TOP_IFACE,
            {"ForegroundWindow": GLib.Variant("(ss)", tuple(self._foreground_window))},
        )


# ── Helper to start / stop the service ──────────────────────────────

_bus = None
_api_instance = None
_controller_instances: dict[str, ControllerInstanceAPI] = {}


def start_dbus_service():
    """Publish the StreamController API on the session bus."""
    global _bus, _api_instance
    try:
        _bus = SessionMessageBus()
        _api_instance = StreamControllerAPI()
        _bus.publish_object(DBUS_OBJECT_PATH, _api_instance)

        # Publish a sub-object for each connected controller
        if gl.deck_manager is not None:
            for controller in gl.deck_manager.deck_controller:
                _publish_controller(controller)

        log.success(f"DBus API published at {DBUS_OBJECT_PATH}")
    except Exception as e:
        log.error(f"Failed to start DBus API service: {e}")


def _publish_controller(controller):
    """Publish a ControllerInstanceAPI for a single deck controller."""
    global _bus
    serial = controller.serial_number()
    if serial in _controller_instances:
        return  # already published
    path_component = _serial_to_dbus_path(serial)
    obj_path = f"{CONTROLLER_BASE_PATH}/{path_component}"
    instance = ControllerInstanceAPI(controller)
    instance._object_path = obj_path
    _controller_instances[serial] = instance
    _bus.publish_object(obj_path, instance)
    log.info(f"DBus API: published controller {serial} at {obj_path}")


def stop_dbus_service():
    """Disconnect from the session bus."""
    global _bus
    try:
        if _bus is not None:
            _bus.disconnect()
            _bus = None
            _controller_instances.clear()
            log.info("DBus API service stopped")
    except Exception as e:
        log.error(f"Failed to stop DBus API service: {e}")


def get_api_instance() -> StreamControllerAPI | None:
    """Return the active top-level API instance, or None if not started."""
    return _api_instance


def get_controller_instance(serial: str) -> ControllerInstanceAPI | None:
    """Return the API instance for a specific controller, or None."""
    return _controller_instances.get(serial)


def notify_active_page_changed(serial: str, page_name: str) -> None:
    """Update the ActivePageName for a controller's API object.

    Call this from DeckController.load_page() so that DBus clients
    see the new active page name.
    """
    instance = _controller_instances.get(serial)
    if instance is not None:
        instance.ActivePageName = page_name


def notify_foreground_window_changed(name: str, wm_class: str) -> None:
    """Update the ForegroundWindow on the top-level API object.

    Call this from WindowGrabber.on_active_window_changed() so that
    DBus clients see foreground window changes.
    """
    if _api_instance is not None:
        _api_instance.ForegroundWindow = WindowInfo(name, wm_class)