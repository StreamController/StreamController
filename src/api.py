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

import json
import os
import re
from collections import namedtuple
from typing import Tuple
from src.Signals import Signals
from loguru import logger as log

from dasbus.server.interface import dbus_interface
from dasbus.connection import SessionMessageBus
from dasbus.typing import Str, List
from dasbus.error import DBusError
from gi.repository import GLib, Gio

import globals as gl

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