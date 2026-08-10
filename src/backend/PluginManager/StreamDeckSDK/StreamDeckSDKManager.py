"""
Author: Core447
Year: 2025

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
any later version.

This programm comes with ABSOLUTELY NO WARRANTY!

You should have received a copy of the GNU General Public License
along with this program. If not, see <https://www.gnu.org/licenses/>.
"""
import json
import os
import shutil
import threading
import zipfile

from gi.repository import GLib

from loguru import logger as log

import globals as gl

from src.backend.DeckManagement.HelperMethods import open_web
from src.backend.PluginManager.StreamDeckSDK import InfoParam
from src.backend.PluginManager.StreamDeckSDK.AssetServer import AssetServer
from src.backend.PluginManager.StreamDeckSDK.Manifest import SDManifest, read_manifest
from src.backend.PluginManager.StreamDeckSDK.PluginProcess import (
    PluginProcess,
    RunMode,
    UnsupportedPluginError,
    determine_run_mode,
    remove_wine_prefix,
)
from src.backend.PluginManager.StreamDeckSDK.PropertyInspector import PropertyInspectorView
from src.backend.PluginManager.StreamDeckSDK.SDPluginBase import SDPluginBase
from src.backend.PluginManager.StreamDeckSDK.WebSocketServer import WebSocketConnection, WebSocketServer
from src.backend.PluginManager.StreamDeckSDK.WebViewHost import WebViewPluginHost
from src.Signals.Signals import AppQuit, ChangePage

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.backend.PluginManager.StreamDeckSDK.SDAction import SDActionCore

PLUGIN_DIR_NAME = "streamdeck-plugins"
LOG_DIR_NAME = os.path.join("logs", "streamdeck-plugins")

# The events a plugin socket is allowed to send
PLUGIN_EVENTS = {
    "setSettings", "getSettings", "setGlobalSettings", "getGlobalSettings",
    "openUrl", "logMessage", "setTitle", "setImage", "setFeedback",
    "setFeedbackLayout", "setTriggerDescription", "setState", "showAlert",
    "showOk", "switchToProfile", "sendToPropertyInspector",
}

# The events a property inspector socket is allowed to send
PROPERTY_INSPECTOR_EVENTS = {
    "setSettings", "getSettings", "setGlobalSettings", "getGlobalSettings",
    "openUrl", "logMessage", "sendToPlugin",
}


class StreamDeckSDKManager:
    """
    Runs plugins written against the Elgato Stream Deck SDK and translates between
    their WebSocket protocol and StreamController's own plugin and action model.
    """

    def __init__(self):
        self.plugin_dir = os.path.join(gl.DATA_PATH, PLUGIN_DIR_NAME)
        self.log_dir = os.path.join(gl.DATA_PATH, LOG_DIR_NAME)

        self.plugins: dict[str, SDPluginBase] = {}
        self.processes: dict[str, PluginProcess] = {}
        self.webviews: dict[str, WebViewPluginHost] = {}
        self.load_errors: dict[str, str] = {}

        self.contexts: dict[str, "SDActionCore"] = {}
        self._contexts_lock = threading.Lock()

        self.plugin_sockets: dict[str, WebSocketConnection] = {}
        self.property_inspector_sockets: dict[str, WebSocketConnection] = {}
        self._sockets_lock = threading.Lock()

        self.websocket_server: WebSocketServer = None
        self.asset_server: AssetServer = None

        self._open_property_inspector: str = None

    # ------- #
    # Startup #
    # ------- #

    def init(self) -> None:
        """
        Read the installed plugins and make their actions available.

        The plugin processes themselves are started later by :meth:`start_plugins`,
        once the decks are known, because the SDK hands a plugin the list of connected
        devices when it launches.
        """
        os.makedirs(self.plugin_dir, exist_ok=True)
        os.makedirs(self.log_dir, exist_ok=True)

        self.websocket_server = WebSocketServer(
            on_message=self._on_socket_message,
            on_close=self._on_socket_closed,
        )
        self.websocket_server.start()

        self.asset_server = AssetServer(root=self.plugin_dir)
        self.asset_server.start()

        gl.signal_manager.connect_signal(ChangePage, self._on_page_changed)
        gl.signal_manager.connect_signal(AppQuit, self._on_app_quit)

        self.load_plugins()

    def load_plugins(self) -> None:
        for entry in sorted(os.listdir(self.plugin_dir)):
            path = os.path.join(self.plugin_dir, entry)
            if not os.path.isdir(path):
                continue
            self.load_plugin(path, start=False)

    def start_plugins(self) -> None:
        """Launch every loaded plugin that is not running yet."""
        for plugin_uuid, plugin in self.plugins.items():
            if plugin.sd_process is None and plugin.sd_webview is None:
                self.start_plugin(plugin_uuid)

    def load_plugin(self, path: str, start: bool = True) -> SDPluginBase | None:
        name = os.path.basename(os.path.normpath(path))

        try:
            manifest = read_manifest(path)
        except (FileNotFoundError, ValueError) as e:
            log.warning(f"Skipping {name}: {e}")
            self.load_errors[name] = str(e)
            return None

        if manifest.uuid in self.plugins:
            log.warning(f"Stream Deck plugin {manifest.uuid} is already loaded, skipping {path}")
            return self.plugins[manifest.uuid]

        try:
            plugin = SDPluginBase(manifest)
        except Exception as e:
            log.error(f"Failed to load Stream Deck plugin {manifest.uuid}: {e}")
            self.load_errors[name] = str(e)
            # A plugin that failed half way through must not stay half registered
            self._remove_plugin_object(manifest.uuid)
            return None

        self.load_errors.pop(name, None)
        self.plugins[manifest.uuid] = plugin
        if start:
            self.start_plugin(manifest.uuid)
        return plugin

    def start_plugin(self, plugin_uuid: str) -> None:
        plugin = self.plugins.get(plugin_uuid)
        if plugin is None:
            return

        manifest = plugin.sd_manifest

        try:
            mode, code_path = determine_run_mode(manifest)
        except UnsupportedPluginError as e:
            plugin.sd_start_error = f"Cannot run this plugin because {e}"
            log.warning(f"Not starting {plugin_uuid}: {e}")
            return

        plugin.sd_run_mode = mode
        plugin.sd_start_error = None

        info = InfoParam.make_info(manifest.uuid, manifest.version, pretend_windows=(mode is RunMode.WINE))

        if mode is RunMode.WEBVIEW:
            url = self.asset_server.get_url(os.path.join(manifest.path, code_path))
            host = WebViewPluginHost(
                plugin_uuid=manifest.uuid,
                title=manifest.name,
                url=url,
                port=self.websocket_server.port,
                info=info,
                show_window=os.path.exists(os.path.join(manifest.path, "debug")),
            )
            try:
                host.start()
            except RuntimeError as e:
                plugin.sd_start_error = str(e)
                log.error(f"Failed to start {plugin_uuid}: {e}")
                return
            self.webviews[manifest.uuid] = host
            plugin.sd_webview = host
            return

        process = PluginProcess(
            manifest=manifest,
            mode=mode,
            code_path=code_path,
            log_path=os.path.join(self.log_dir, f"{manifest.uuid}.log"),
        )

        try:
            process.start(self.websocket_server.port, info)
        except (UnsupportedPluginError, OSError) as e:
            plugin.sd_start_error = f"Cannot run this plugin because {e}" if isinstance(e, UnsupportedPluginError) else str(e)
            log.error(f"Failed to start {plugin_uuid}: {e}")
            return

        self.processes[manifest.uuid] = process
        plugin.sd_process = process

    def stop_plugin(self, plugin_uuid: str) -> None:
        process = self.processes.pop(plugin_uuid, None)
        if process is not None:
            process.stop()

        webview = self.webviews.pop(plugin_uuid, None)
        if webview is not None:
            webview.stop()

        with self._sockets_lock:
            socket = self.plugin_sockets.pop(plugin_uuid, None)
        if socket is not None:
            socket.close()

        plugin = self.plugins.get(plugin_uuid)
        if plugin is not None:
            plugin.sd_process = None
            plugin.sd_webview = None
            plugin.sd_connected = False

    def restart_plugin(self, plugin_uuid: str) -> None:
        self.stop_plugin(plugin_uuid)
        self.start_plugin(plugin_uuid)

    def shutdown(self) -> None:
        for plugin_uuid in list(self.plugins.keys()):
            self.stop_plugin(plugin_uuid)

        if self.websocket_server is not None:
            self.websocket_server.stop()
        if self.asset_server is not None:
            self.asset_server.stop()

    def _on_app_quit(self, *args) -> None:
        self.shutdown()

    # ----------------- #
    # Context registry  #
    # ----------------- #

    def register_context(self, action) -> None:
        with self._contexts_lock:
            self.contexts[action.sd_context] = action

    def unregister_context(self, action) -> None:
        with self._contexts_lock:
            self.contexts.pop(action.sd_context, None)

    def get_context(self, context: str):
        with self._contexts_lock:
            return self.contexts.get(context)

    def get_contexts_for_plugin(self, plugin_uuid: str) -> list:
        with self._contexts_lock:
            actions = list(self.contexts.values())
        return [a for a in actions if a.plugin_uuid == plugin_uuid]

    def _on_page_changed(self, *args) -> None:
        """Tell plugins which of their actions left or entered the screen."""
        with self._contexts_lock:
            actions = list(self.contexts.values())

        for action in actions:
            try:
                if action.get_is_present():
                    action.send_will_appear()
                else:
                    action.send_will_disappear()
            except Exception as e:
                log.error(f"Failed to update the visibility of {action.sd_context}: {e}")

    # -------------- #
    # Socket routing #
    # -------------- #

    def _on_socket_message(self, connection: WebSocketConnection, message: str) -> None:
        try:
            data = json.loads(message)
        except json.JSONDecodeError:
            log.warning("Received a Stream Deck SDK message that is not valid JSON")
            return

        if not isinstance(data, dict):
            return

        if connection.identity is None:
            self._handle_registration(connection, data)
            return

        kind, identifier = connection.identity
        if kind == "plugin":
            self._handle_plugin_event(identifier, data)
        else:
            self._handle_property_inspector_event(identifier, data)

    def _handle_registration(self, connection: WebSocketConnection, data: dict) -> None:
        event = data.get("event")
        uuid = data.get("uuid")

        if event == "registerPlugin" and isinstance(uuid, str):
            if uuid not in self.plugins:
                log.warning(f"An unknown plugin tried to register as {uuid}")
                connection.close()
                return

            connection.identity = ("plugin", uuid)
            with self._sockets_lock:
                previous = self.plugin_sockets.get(uuid)
                self.plugin_sockets[uuid] = connection
            if previous is not None and previous is not connection:
                previous.close()

            self.plugins[uuid].sd_connected = True
            log.info(f"Stream Deck plugin {uuid} registered")

            self._announce_devices(uuid)
            self._announce_appeared_actions(uuid)

        elif event == "registerPropertyInspector" and isinstance(uuid, str):
            action = self.get_context(uuid)
            if action is None:
                log.warning(f"A property inspector tried to register for the unknown context {uuid}")
                connection.close()
                return

            connection.identity = ("property-inspector", uuid)
            with self._sockets_lock:
                previous = self.property_inspector_sockets.get(uuid)
                self.property_inspector_sockets[uuid] = connection
            if previous is not None and previous is not connection:
                previous.close()

        else:
            log.warning(f"Rejecting a socket that sent {event!r} instead of registering")
            connection.close()

    def _announce_devices(self, plugin_uuid: str) -> None:
        for device in InfoParam.get_device_info_list():
            self.send_to_plugin(plugin_uuid, {
                "event": "deviceDidConnect",
                "device": device["id"],
                "deviceInfo": {
                    "name": device["name"],
                    "type": device["type"],
                    "size": device["size"],
                },
            })

    def _announce_appeared_actions(self, plugin_uuid: str) -> None:
        """A plugin that (re)connects has to be told about the actions already on screen."""
        for action in self.get_contexts_for_plugin(plugin_uuid):
            try:
                if action.get_is_present():
                    action.resend_will_appear()
            except Exception as e:
                log.error(f"Failed to announce {action.sd_context} to {plugin_uuid}: {e}")

    def _on_socket_closed(self, connection: WebSocketConnection) -> None:
        if connection.identity is None:
            return

        kind, identifier = connection.identity
        with self._sockets_lock:
            if kind == "plugin":
                if self.plugin_sockets.get(identifier) is connection:
                    del self.plugin_sockets[identifier]
            else:
                if self.property_inspector_sockets.get(identifier) is connection:
                    del self.property_inspector_sockets[identifier]

        if kind == "plugin":
            plugin = self.plugins.get(identifier)
            if plugin is not None:
                plugin.sd_connected = False
            log.info(f"Stream Deck plugin {identifier} disconnected")

    # ------- #
    # Sending #
    # ------- #

    def send_to_plugin(self, plugin_uuid: str, message: dict) -> None:
        with self._sockets_lock:
            connection = self.plugin_sockets.get(plugin_uuid)

        # Nothing is queued for a plugin that has not connected: whatever it missed is
        # replayed from the current state when it registers
        if connection is None or connection.closed:
            return

        connection.send_text(json.dumps(message))

    def send_to_property_inspector(self, context: str, message: dict) -> None:
        with self._sockets_lock:
            connection = self.property_inspector_sockets.get(context)

        if connection is None or connection.closed:
            return

        connection.send_text(json.dumps(message))

    # ---------------- #
    # Inbound handling #
    # ---------------- #

    def _handle_plugin_event(self, plugin_uuid: str, data: dict) -> None:
        event = data.get("event")
        if event not in PLUGIN_EVENTS:
            log.warning(f"Plugin {plugin_uuid} sent the unsupported event {event!r}")
            return

        payload = data.get("payload")
        context = data.get("context")

        if event in ("setGlobalSettings", "getGlobalSettings"):
            # For a plugin socket the context is its own uuid
            if context != plugin_uuid:
                log.warning(f"Plugin {plugin_uuid} tried to access the settings of {context}")
                return
            self._handle_global_settings(plugin_uuid, event, payload, to_property_inspector=False)
            return

        if event == "openUrl":
            self._open_url(payload)
            return

        if event == "logMessage":
            self._log_message(plugin_uuid, payload)
            return

        if event == "switchToProfile":
            self._switch_to_profile(data)
            return

        action = self.get_context(context) if isinstance(context, str) else None
        if action is None:
            return

        # A plugin may only touch its own actions
        if action.plugin_uuid != plugin_uuid:
            log.warning(f"Plugin {plugin_uuid} tried to control an action of {action.plugin_uuid}")
            return

        payload = payload if isinstance(payload, dict) else {}

        if event == "setTitle":
            action.handle_set_title(payload)
        elif event == "setImage":
            action.handle_set_image(payload)
        elif event == "setState":
            action.handle_set_state(payload)
        elif event == "setSettings":
            action.handle_set_settings(payload, from_property_inspector=False)
        elif event == "getSettings":
            action.handle_get_settings(from_property_inspector=False)
        elif event == "showAlert":
            action.handle_show_alert()
        elif event == "showOk":
            action.handle_show_ok()
        elif event == "setFeedback":
            action.handle_set_feedback(payload)
        elif event == "setFeedbackLayout":
            action.handle_set_feedback_layout(payload)
        elif event == "sendToPropertyInspector":
            action.handle_send_to_property_inspector(payload)
        elif event == "setTriggerDescription":
            # Only affects the on device help text of the official software
            pass

    def _handle_property_inspector_event(self, context: str, data: dict) -> None:
        event = data.get("event")
        if event not in PROPERTY_INSPECTOR_EVENTS:
            log.warning(f"A property inspector sent the unsupported event {event!r}")
            return

        payload = data.get("payload")

        if event == "openUrl":
            self._open_url(payload)
            return

        if event == "logMessage":
            self._log_message(context, payload)
            return

        action = self.get_context(context)
        if action is None:
            return

        if event in ("setGlobalSettings", "getGlobalSettings"):
            self._handle_global_settings(action.plugin_uuid, event, payload, to_property_inspector=True, context=context)
        elif event == "setSettings":
            action.handle_set_settings(payload if isinstance(payload, dict) else {}, from_property_inspector=True)
        elif event == "getSettings":
            action.handle_get_settings(from_property_inspector=True)
        elif event == "sendToPlugin":
            action.handle_send_to_plugin(payload)

    def _handle_global_settings(self, plugin_uuid: str, event: str, payload, to_property_inspector: bool,
                                context: str = None) -> None:
        plugin = self.plugins.get(plugin_uuid)
        if plugin is None:
            return

        if event == "setGlobalSettings":
            if not isinstance(payload, dict):
                return
            plugin.set_global_settings(payload)

        message = {
            "event": "didReceiveGlobalSettings",
            "payload": {"settings": plugin.get_global_settings()},
        }

        if event == "setGlobalSettings":
            # Everybody except the sender learns about the new settings
            if to_property_inspector:
                self.send_to_plugin(plugin_uuid, message)
            else:
                for action in self.get_contexts_for_plugin(plugin_uuid):
                    self.send_to_property_inspector(action.sd_context, message)
        else:
            if to_property_inspector:
                self.send_to_property_inspector(context, message)
            else:
                self.send_to_plugin(plugin_uuid, message)

    def _open_url(self, payload) -> None:
        url = payload.get("url") if isinstance(payload, dict) else None
        if not isinstance(url, str) or not url.startswith(("http://", "https://")):
            return
        GLib.idle_add(open_web, url)

    def _log_message(self, source: str, payload) -> None:
        message = payload.get("message") if isinstance(payload, dict) else payload
        if message is None:
            return
        log.info(f"[{source}] {message}")

    def _switch_to_profile(self, data: dict) -> None:
        """
        The SDK's profiles map onto StreamController's pages, so switch to the page of
        the same name if the user has one.
        """
        payload = data.get("payload")
        profile = payload.get("profile") if isinstance(payload, dict) else None
        device = data.get("device")

        if not profile:
            return

        page_path = gl.page_manager.find_matching_page_path(profile)
        if page_path is None:
            log.warning(f"A plugin asked to switch to the profile {profile!r}, but no page has that name")
            return

        for controller in gl.deck_manager.deck_controller:
            try:
                if device and controller.serial_number() != device:
                    continue
            except Exception:
                continue
            page = gl.page_manager.get_page(page_path, controller)
            GLib.idle_add(controller.load_page, page)

    # ------------------ #
    # Property inspector #
    # ------------------ #

    def build_property_inspector(self, action):
        path = action.get_property_inspector_path()
        if path is None:
            self.close_property_inspector()
            return None

        self.close_property_inspector()

        view = PropertyInspectorView(
            action=action,
            path=path,
            url=self.asset_server.get_url(path),
            port=self.websocket_server.port,
            info=InfoParam.make_info(
                action.plugin_uuid,
                action.sd_plugin.sd_manifest.version,
                pretend_windows=(action.sd_plugin.sd_run_mode is RunMode.WINE),
            ),
            action_info=action.get_action_info(),
        )

        self._open_property_inspector = action.sd_context
        self.send_to_plugin(action.plugin_uuid, {
            "event": "propertyInspectorDidAppear",
            "action": action.sd_action.uuid,
            "context": action.sd_context,
            "device": action.get_device_id(),
        })

        return view

    def close_property_inspector(self, context: str = None) -> None:
        """
        Tell the plugin that its property inspector is gone.

        ``context`` guards against a view that is being replaced closing the one that
        took its place: a stale view only closes itself.
        """
        if context is not None and self._open_property_inspector != context:
            return

        context = self._open_property_inspector
        if context is None:
            return
        self._open_property_inspector = None

        with self._sockets_lock:
            connection = self.property_inspector_sockets.pop(context, None)
        if connection is not None:
            connection.close()

        action = self.get_context(context)
        if action is None:
            return

        self.send_to_plugin(action.plugin_uuid, {
            "event": "propertyInspectorDidDisappear",
            "action": action.sd_action.uuid,
            "context": context,
            "device": action.get_device_id(),
        })

    # ------------ #
    # Installation #
    # ------------ #

    def install_from_file(self, file_path: str) -> list[str]:
        """
        Unpack a ``.streamDeckPlugin`` archive (or a plain zip or directory containing
        one or more ``.sdPlugin`` directories) into the plugin directory.

        This only touches the filesystem, so it is safe to call from a worker thread.
        Hand the result to :meth:`activate_plugins` on the main thread to actually run
        what was installed.

        Returns:
            list[str]: The installed plugin directories.

        Raises:
            ValueError: If the archive does not contain a usable plugin.
        """
        if os.path.isdir(file_path):
            return [self._copy_into_place(file_path)]

        if not zipfile.is_zipfile(file_path):
            raise ValueError("This file is not a Stream Deck plugin archive")

        staging_dir = os.path.join(self.plugin_dir, ".staging")
        shutil.rmtree(staging_dir, ignore_errors=True)
        os.makedirs(staging_dir, exist_ok=True)

        try:
            with zipfile.ZipFile(file_path) as archive:
                self._safe_extract(archive, staging_dir)

            sources = self._find_plugin_dirs(staging_dir)
            if not sources:
                raise ValueError("This archive does not contain a .sdPlugin directory with a manifest")

            return [self._copy_into_place(source) for source in sources]
        finally:
            shutil.rmtree(staging_dir, ignore_errors=True)

    def _copy_into_place(self, source: str) -> str:
        manifest = read_manifest(source)
        target = os.path.join(self.plugin_dir, os.path.basename(os.path.normpath(source)))

        if manifest.uuid in self.plugins:
            self.stop_plugin(manifest.uuid)

        if os.path.abspath(source) != os.path.abspath(target):
            shutil.rmtree(target, ignore_errors=True)
            shutil.copytree(source, target)

        return target

    def activate_plugins(self, paths: list[str]) -> list[str]:
        """
        Load and start the plugins in ``paths``. Builds widgets, so it belongs on the
        main thread.

        Returns:
            list[str]: The uuids of the plugins that came up.
        """
        uuids = []
        for path in paths:
            try:
                uuid = read_manifest(path).uuid
            except (FileNotFoundError, ValueError):
                continue

            # A plugin being replaced has to lose its old registration first
            self._remove_plugin_object(uuid)

            plugin = self.load_plugin(path)
            if plugin is not None:
                uuids.append(plugin.sd_manifest.uuid)

        gl.plugin_manager.generate_action_index()
        _reload_pages_and_ui()

        return uuids

    @staticmethod
    def _safe_extract(archive: zipfile.ZipFile, destination: str) -> None:
        destination = os.path.realpath(destination)
        for member in archive.infolist():
            member_path = os.path.realpath(os.path.join(destination, member.filename))
            if not member_path.startswith(destination + os.sep) and member_path != destination:
                raise ValueError(f"The archive tries to write outside of the plugin directory: {member.filename}")
        archive.extractall(destination)

    @staticmethod
    def _find_plugin_dirs(root: str) -> list[str]:
        found = []
        for current, directories, _files in os.walk(root):
            for directory in list(directories):
                if not directory.endswith(".sdPlugin"):
                    continue
                candidate = os.path.join(current, directory)
                if os.path.isfile(os.path.join(candidate, "manifest.json")):
                    found.append(candidate)
                    directories.remove(directory)
        return found

    def uninstall(self, plugin_uuid: str) -> None:
        plugin = self.plugins.get(plugin_uuid)
        if plugin is None:
            return

        path = plugin.sd_manifest.path

        self.stop_plugin(plugin_uuid)
        remove_wine_prefix(path)

        # Drop the action instances the pages are still holding on to
        if gl.deck_manager is not None:
            for controller in gl.deck_manager.deck_controller:
                page = getattr(controller, "active_page", None)
                if page is not None:
                    page.remove_plugin_action_objects(plugin_id=plugin_uuid)

        self._remove_plugin_object(plugin_uuid)
        self.load_errors.pop(os.path.basename(os.path.normpath(path)), None)
        plugin.on_uninstall()

        shutil.rmtree(path, ignore_errors=True)
        gl.plugin_manager.generate_action_index()
        _reload_pages_and_ui()

    def _remove_plugin_object(self, plugin_uuid: str) -> None:
        self.plugins.pop(plugin_uuid, None)

        from src.backend.PluginManager.PluginBase import PluginBase
        PluginBase.plugins.pop(plugin_uuid, None)
        PluginBase.disabled_plugins.pop(plugin_uuid, None)

    # ----- #
    # Misc  #
    # ----- #

    def get_manifests(self) -> list[SDManifest]:
        return [plugin.sd_manifest for plugin in self.plugins.values()]


def _reload_pages_and_ui() -> None:
    """Pick up added or removed actions on the decks and in the action chooser."""
    if gl.deck_manager is not None:
        for controller in gl.deck_manager.deck_controller:
            page = getattr(controller, "active_page", None)
            if page is None:
                continue
            page.load_action_objects()
            controller.load_page(page)

    try:
        GLib.idle_add(gl.app.main_win.sidebar.action_chooser.plugin_group.update)
    except AttributeError:
        pass
