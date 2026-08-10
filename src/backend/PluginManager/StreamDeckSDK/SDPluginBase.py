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
import os
import re

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk

import globals as gl

from src.backend.DeckManagement.InputIdentifier import Input
from src.backend.PluginManager.ActionHolder import ActionHolder
from src.backend.PluginManager.ActionInputSupport import ActionInputSupport
from src.backend.PluginManager.PluginBase import PluginBase
from src.backend.PluginManager.StreamDeckSDK.Manifest import SDManifest, resolve_icon_path
from src.backend.PluginManager.StreamDeckSDK.PluginProcess import PluginProcess, RunMode
from src.backend.PluginManager.StreamDeckSDK.SDAction import SDActionCore

GLOBAL_SETTINGS_KEY = "sdk-global-settings"

_IDENTIFIER_SAFE = re.compile(r"\W")


class SDPluginBase(PluginBase):
    """
    Presents an installed Stream Deck SDK plugin to the rest of StreamController as an
    ordinary plugin, so its actions show up in the action chooser, get placed on pages
    and are stored in page files just like native ones.
    """

    # PluginManager instantiates every PluginBase subclass it finds; these are created
    # by the StreamDeckSDKManager with a manifest instead.
    AUTO_INIT = False

    # Stream Deck SDK plugins carry their own localisation, not StreamController's
    HAS_LOCALES = False

    def __init__(self, manifest: SDManifest):
        self.sd_manifest = manifest
        self.sd_process: PluginProcess = None
        self.sd_run_mode: RunMode = None
        self.sd_webview = None
        self.sd_start_error: str = None
        self.sd_connected: bool = False

        super().__init__(use_legacy_locale=True)

        # PluginBase derives these from the file the subclass is defined in, which for
        # us is this module rather than the plugin
        self.PATH = manifest.path

        self.register(
            plugin_name=self._get_free_plugin_name(manifest.name),
            github_repo=manifest.url or "https://github.com/StreamController/StreamController",
            plugin_version=manifest.version,
            app_version=gl.app_version,
        )

        if not self.registered:
            # Without this the plugin would run but none of its actions would be
            # reachable, which is far more confusing than refusing to load it
            raise RuntimeError(f"StreamController rejected the plugin {manifest.uuid}")

        self._add_action_holders()

    def _get_free_plugin_name(self, name: str) -> str:
        """
        StreamController requires plugin names to be unique, and Stream Deck plugins
        happily share names with native ones - there is an Elgato "Clocks" as well as a
        StreamController "Clocks". Mark ours apart when that happens.
        """
        taken = {plugin["object"].plugin_name for plugin in PluginBase.plugins.values()}

        if name not in taken:
            return name

        marked = f"{name} (Stream Deck)"
        if marked not in taken:
            return marked

        return f"{name} ({self.sd_manifest.uuid})"

    # --------------------------- #
    # PluginBase identity overrides #
    # --------------------------- #

    def get_plugin_id(self) -> str:
        return self.sd_manifest.uuid

    def get_plugin_id_from_folder_name(self) -> str:
        return self.sd_manifest.uuid

    def get_manifest(self) -> dict:
        return {
            "id": self.sd_manifest.uuid,
            "name": self.sd_manifest.name,
            "version": self.sd_manifest.version,
            "github": self.sd_manifest.url,
            "app-version": gl.app_version,
            "minimum-app-version": gl.app_version,
        }

    def get_about(self) -> dict:
        return {
            "name": self.sd_manifest.name,
            "author": self.sd_manifest.author,
            "version": self.sd_manifest.version,
            "description": self.sd_manifest.description,
        }

    def get_selector_icon(self) -> Gtk.Widget:
        icon_path = self.sd_manifest.get_icon_path()
        if icon_path:
            try:
                return Gtk.Image.new_from_file(icon_path)
            except Exception:
                pass
        return Gtk.Image(icon_name="application-x-addon-symbolic")

    # ------- #
    # Actions #
    # ------- #

    def _add_action_holders(self) -> None:
        for action in self.sd_manifest.actions:
            if not action.visible_in_action_list:
                continue

            action_core = type(
                f"SDAction_{_IDENTIFIER_SAFE.sub('_', action.uuid)}",
                (SDActionCore,),
                {"SD_ACTION": action},
            )

            keypad = ActionInputSupport.SUPPORTED if action.supports_keypad() else ActionInputSupport.UNSUPPORTED
            encoder = ActionInputSupport.SUPPORTED if action.supports_encoder() else ActionInputSupport.UNSUPPORTED

            self.add_action_holder(ActionHolder(
                plugin_base=self,
                action_core=action_core,
                action_id=f"{self.sd_manifest.uuid}::{action.uuid}",
                action_name=action.name,
                icon=self._build_action_icon(action),
                action_support={
                    Input.Key: keypad,
                    Input.Dial: encoder,
                    Input.Touchscreen: ActionInputSupport.UNSUPPORTED,
                },
            ))

    def _build_action_icon(self, action) -> Gtk.Widget:
        icon_path = resolve_icon_path(os.path.join(self.sd_manifest.path, action.icon)) if action.icon else None
        if icon_path:
            try:
                image = Gtk.Image.new_from_file(icon_path)
                image.set_pixel_size(24)
                return image
            except Exception:
                pass
        return Gtk.Image(icon_name="insert-image-symbolic")

    # --------------- #
    # Global settings #
    # --------------- #

    def get_global_settings(self) -> dict:
        return (self.get_settings() or {}).get(GLOBAL_SETTINGS_KEY) or {}

    def set_global_settings(self, settings: dict) -> None:
        stored = self.get_settings() or {}
        stored[GLOBAL_SETTINGS_KEY] = settings
        self.set_settings(stored)

    # ------------------ #
    # Process management #
    # ------------------ #

    def get_status_text(self) -> str:
        if self.sd_start_error:
            return self.sd_start_error
        if self.sd_run_mode is RunMode.WEBVIEW:
            return "Running in a WebView"
        if self.sd_connected:
            return f"Connected ({self.sd_run_mode.value})" if self.sd_run_mode else "Connected"
        if self.sd_process is not None and self.sd_process.is_alive():
            return f"Started, waiting for it to connect ({self.sd_run_mode.value})"
        return "Not running"

    def get_action_instances(self) -> list[SDActionCore]:
        return gl.sd_sdk_manager.get_contexts_for_plugin(self.sd_manifest.uuid)

    def on_uninstall(self) -> None:
        super().on_uninstall()
        gl.sd_sdk_manager.stop_plugin(self.sd_manifest.uuid)
