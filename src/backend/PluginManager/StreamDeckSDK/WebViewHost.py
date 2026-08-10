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

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, GLib

from loguru import logger as log

from src.backend.PluginManager.StreamDeckSDK.PropertyInspector import WEBKIT

_BOOTSTRAP = """
(function() {
    const args = %(args)s;
    let attempts = 0;
    function connect() {
        if (typeof connectOpenActionSocket === "function") {
            connectOpenActionSocket.apply(null, args);
        } else if (typeof connectElgatoStreamDeckSocket === "function") {
            connectElgatoStreamDeckSocket.apply(null, args);
        } else if (typeof connectSocket === "function") {
            connectSocket.apply(null, args);
        } else if (++attempts < 1000) {
            setTimeout(connect, 10);
        } else {
            console.error("StreamController: this plugin never defined connectElgatoStreamDeckSocket");
        }
    }
    connect();
})();
"""


class WebViewPluginHost:
    """
    Runs a Stream Deck SDK plugin whose code path is an HTML document.

    The document lives in a WebView inside a window that is never shown, unless the
    plugin directory contains a ``debug`` marker file, which mirrors the convention
    other Stream Deck host applications use.
    """

    def __init__(self, plugin_uuid: str, title: str, url: str, port: int, info: dict, show_window: bool = False):
        self.plugin_uuid = plugin_uuid
        self.title = title
        self.url = url
        self.port = port
        self.info = info
        self.show_window = show_window

        self.window: Gtk.Window = None
        self.webview = None

    def start(self) -> None:
        if WEBKIT is None:
            raise RuntimeError("WebKitGTK is not available, cannot run HTML based plugins")
        GLib.idle_add(self._build)

    def _build(self) -> bool:
        args = [self.port, self.plugin_uuid, "registerPlugin", json.dumps(self.info), ""]

        content_manager = WEBKIT.UserContentManager()
        content_manager.add_script(WEBKIT.UserScript.new(
            _BOOTSTRAP % {"args": json.dumps(args[:4])},
            WEBKIT.UserContentInjectedFrames.TOP_FRAME,
            WEBKIT.UserScriptInjectionTime.END,
            None,
            None,
        ))

        self.webview = WEBKIT.WebView(user_content_manager=content_manager)
        self.webview.get_settings().set_enable_developer_extras(True)

        self.window = Gtk.Window(title=f"{self.title} (Stream Deck plugin)")
        self.window.set_default_size(900, 600)
        self.window.set_child(self.webview)

        self.webview.load_uri(self.url)

        if self.show_window:
            self.window.present()

        log.info(f"Started HTML plugin {self.plugin_uuid}")
        return False

    def stop(self) -> None:
        GLib.idle_add(self._destroy)

    def _destroy(self) -> bool:
        if self.webview is not None:
            self.webview.stop_loading()
            self.webview.load_uri("about:blank")
            self.webview = None
        if self.window is not None:
            self.window.destroy()
            self.window = None
        return False
