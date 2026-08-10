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
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw

from loguru import logger as log

import globals as gl

from src.backend.DeckManagement.HelperMethods import open_web

WEBKIT = None
WEBKIT_ERROR: str = None

try:
    gi.require_version("WebKit", "6.0")
    from gi.repository import WebKit as _WebKit
    WEBKIT = _WebKit
except (ImportError, ValueError) as e:
    WEBKIT_ERROR = str(e)


def is_available() -> bool:
    return WEBKIT is not None


# Injected into every property inspector. The SDK entry point is often defined by a
# script that is still loading when the document finishes, so keep retrying.
_BOOTSTRAP = """
(function() {
    const args = %(args)s;
    let attempts = 0;
    function connect() {
        if (typeof connectOpenActionSocket === "function") {
            // OpenAction plugins, which follow the same protocol
            connectOpenActionSocket.apply(null, args);
        } else if (typeof connectElgatoStreamDeckSocket === "function") {
            connectElgatoStreamDeckSocket.apply(null, args);
        } else if (typeof connectSocket === "function") {
            // Stream Deck SDK v1 entry point
            connectSocket.apply(null, args);
        } else if (++attempts < 1000) {
            setTimeout(connect, 10);
        } else {
            console.error("StreamController: this property inspector never defined connectElgatoStreamDeckSocket");
        }
    }
    connect();
})();
"""


class PropertyInspectorView(Gtk.Box):
    """
    Hosts the HTML property inspector of a Stream Deck SDK action in a WebView and
    wires it up to the plugin WebSocket server.
    """

    def __init__(self, action, path: str, url: str, port: int, info: dict, action_info: dict, **kwargs):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, hexpand=True, **kwargs)

        self.action = action
        self.context = action.sd_context
        self.path = path
        self.url = url

        self.webview = None

        # The configurator only hides or drops the widget when the user navigates
        # away, so this is where the plugin learns that its inspector is gone
        self.connect("unmap", self.on_unmap)

        if WEBKIT is None:
            self.append(_MissingWebKitBanner())
            return

        args = [
            port,
            action.sd_context,
            "registerPropertyInspector",
            json.dumps(info),
            json.dumps(action_info),
        ]

        content_manager = WEBKIT.UserContentManager()
        content_manager.add_script(WEBKIT.UserScript.new(
            _BOOTSTRAP % {"args": json.dumps(args)},
            WEBKIT.UserContentInjectedFrames.TOP_FRAME,
            WEBKIT.UserScriptInjectionTime.END,
            None,
            None,
        ))

        self.webview = WEBKIT.WebView(user_content_manager=content_manager)
        self.webview.set_hexpand(True)
        self.webview.set_vexpand(True)
        self.webview.set_size_request(-1, 480)
        self.webview.set_background_color(_transparent_rgba())

        settings = self.webview.get_settings()
        settings.set_enable_developer_extras(True)
        settings.set_javascript_can_open_windows_automatically(False)

        self.webview.connect("decide-policy", self.on_decide_policy)
        self.webview.connect("load-failed", self.on_load_failed)

        frame = Gtk.Frame(margin_top=6, margin_bottom=6)
        frame.set_child(self.webview)
        self.append(frame)

        self.webview.load_uri(url)

    def on_decide_policy(self, webview, decision, decision_type) -> bool:
        """Open links that leave the property inspector in the user's browser."""
        if decision_type != WEBKIT.PolicyDecisionType.NAVIGATION_ACTION:
            return False

        navigation_action = decision.get_navigation_action()
        if navigation_action.get_navigation_type() != WEBKIT.NavigationType.LINK_CLICKED:
            return False

        uri = navigation_action.get_request().get_uri()
        if uri and uri.startswith(("http://", "https://")) and not uri.startswith(self.url):
            decision.ignore()
            open_web(uri)
            return True

        return False

    def on_load_failed(self, webview, load_event, failing_uri, error) -> bool:
        log.error(f"Failed to load the property inspector at {failing_uri}: {error.message}")
        return False

    def on_unmap(self, *args) -> None:
        gl.sd_sdk_manager.close_property_inspector(self.context)
        self.shutdown()

    def shutdown(self) -> None:
        if self.webview is not None:
            self.webview.stop_loading()
            # Drop the page so its WebSocket to us is closed right away
            self.webview.load_uri("about:blank")


class _MissingWebKitBanner(Adw.PreferencesGroup):
    def __init__(self):
        super().__init__(title="Property inspector unavailable")
        self.set_description(
            "This action is configured through an HTML property inspector, which needs "
            "WebKitGTK. Install the WebKitGTK 6.0 GObject introspection data to use it."
            + (f"\n\n{WEBKIT_ERROR}" if WEBKIT_ERROR else "")
        )


def _transparent_rgba():
    from gi.repository import Gdk
    rgba = Gdk.RGBA()
    rgba.parse("rgba(0,0,0,0)")
    return rgba
