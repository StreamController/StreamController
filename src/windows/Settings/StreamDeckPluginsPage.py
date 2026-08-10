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
import threading

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, Gio, GLib

from loguru import logger as log

import globals as gl

from GtkHelper.ConfirmationDialog import ConfirmationDialog
from GtkHelper.GtkHelper import BetterPreferencesGroup
from src.backend.DeckManagement.HelperMethods import open_web
from src.backend.PluginManager.StreamDeckSDK.Manifest import SDManifest
from src.backend.PluginManager.StreamDeckSDK.PropertyInspector import is_available as webkit_is_available

MARKETPLACE_URL = "https://marketplace.elgato.com/stream-deck"


class StreamDeckPluginsPage(Adw.PreferencesPage):
    """Install and manage plugins that were built for the Elgato Stream Deck SDK."""

    def __init__(self, settings=None):
        super().__init__()
        self.settings = settings
        self.set_title("Stream Deck Plugins")
        self.set_icon_name("application-x-firmware-symbolic")

        self.add(IntroGroup(page=self))
        self.installed_group = InstalledPluginsGroup(page=self)
        self.add(self.installed_group)

    def reload(self) -> None:
        self.installed_group.load()


class IntroGroup(Adw.PreferencesGroup):
    def __init__(self, page: StreamDeckPluginsPage):
        super().__init__(title="Elgato Stream Deck plugins")
        self.page = page

        self.set_description(
            "StreamController can run plugins written for Elgato's own Stream Deck software. "
            "Download a .streamDeckPlugin file and install it here."
        )

        self.install_row = Adw.ActionRow(
            title="Install a plugin",
            subtitle="Choose a .streamDeckPlugin file",
        )
        install_button = Gtk.Button(label="Install", css_classes=["suggested-action"], valign=Gtk.Align.CENTER)
        install_button.connect("clicked", self.on_install_clicked)
        self.install_row.add_suffix(install_button)
        self.add(self.install_row)

        self.marketplace_row = Adw.ActionRow(
            title="Elgato Marketplace",
            subtitle="Browse plugins made for the Stream Deck software",
        )
        marketplace_button = Gtk.Button(icon_name="web-browser-symbolic", valign=Gtk.Align.CENTER)
        marketplace_button.connect("clicked", lambda *_: open_web(MARKETPLACE_URL))
        self.marketplace_row.add_suffix(marketplace_button)
        self.add(self.marketplace_row)

        self.add(_NodeRow())
        self.add(_RequirementRow(
            title="Wine",
            subtitle="Needed by plugins that are only built for Windows",
            command="wine",
        ))
        self.add(_WebKitRow())

    def on_install_clicked(self, button) -> None:
        file_filter = Gtk.FileFilter()
        file_filter.set_name("Stream Deck plugins")
        file_filter.add_pattern("*.streamDeckPlugin")
        file_filter.add_pattern("*.zip")

        filters = Gio.ListStore.new(Gtk.FileFilter)
        filters.append(file_filter)

        dialog = Gtk.FileDialog(title="Select a Stream Deck plugin", filters=filters, default_filter=file_filter)
        dialog.open(self.page.get_root(), None, self.on_file_chosen)

    def on_file_chosen(self, dialog: Gtk.FileDialog, task) -> None:
        try:
            file = dialog.open_finish(task)
        except GLib.Error:
            return

        if file is None:
            return

        path = file.get_path()
        self.install_row.set_subtitle(f"Installing {os.path.basename(path)}…")
        threading.Thread(target=self._install, args=(path,), name="install_sd_plugin", daemon=True).start()

    def _install(self, path: str) -> None:
        """Unpacking happens off the main thread, activating the plugins happens on it."""
        try:
            installed = gl.sd_sdk_manager.install_from_file(path)
        except Exception as e:
            log.error(f"Failed to install {path}: {e}")
            GLib.idle_add(self._install_finished, None, str(e))
            return

        GLib.idle_add(self._activate, installed)

    def _activate(self, installed: list) -> bool:
        try:
            uuids = gl.sd_sdk_manager.activate_plugins(installed)
        except Exception as e:
            log.error(f"Failed to activate the installed plugins: {e}")
            self._install_finished(None, str(e))
            return False

        self._install_finished(", ".join(uuids) or None, None)
        return False

    def _install_finished(self, installed: str, error: str) -> bool:
        self.install_row.set_subtitle("Choose a .streamDeckPlugin file")
        self.page.reload()

        window = self.page.get_root()
        if error is not None:
            self.install_row.set_subtitle(f"Installation failed: {error}")
        elif installed and hasattr(window, "add_toast"):
            window.add_toast(Adw.Toast(title=f"Installed {installed}"))

        return False


class InstalledPluginsGroup(BetterPreferencesGroup):
    def __init__(self, page: StreamDeckPluginsPage):
        super().__init__(title="Installed")
        self.page = page
        self.load()

    def load(self) -> None:
        self.clear()

        manifests = sorted(gl.sd_sdk_manager.get_manifests(), key=lambda m: m.name.lower())
        errors = gl.sd_sdk_manager.load_errors

        if not manifests and not errors:
            self.add(Adw.ActionRow(
                title="No Stream Deck plugins installed",
                subtitle="Installed plugins show up here and their actions appear in the action chooser",
            ))
            return

        for manifest in manifests:
            self.add(InstalledPluginRow(group=self, manifest=manifest))

        for name, error in sorted(errors.items()):
            row = Adw.ActionRow(title=name, subtitle=f"Could not be loaded: {error}")
            row.add_prefix(Gtk.Image(icon_name="dialog-warning-symbolic"))
            self.add(row)


class InstalledPluginRow(Adw.ExpanderRow):
    def __init__(self, group: InstalledPluginsGroup, manifest: SDManifest):
        super().__init__(title=manifest.name, subtitle=f"{manifest.uuid} · {manifest.version}")
        self.group = group
        self.manifest = manifest

        plugin = gl.sd_sdk_manager.plugins.get(manifest.uuid)

        icon_path = manifest.get_icon_path()
        if icon_path:
            image = Gtk.Image.new_from_file(icon_path)
            image.set_pixel_size(32)
            self.add_prefix(image)

        self.status_row = Adw.ActionRow(title="Status", subtitle=plugin.get_status_text() if plugin else "Not loaded")
        self.add_row(self.status_row)

        if manifest.author:
            self.add_row(Adw.ActionRow(title="Author", subtitle=manifest.author))

        action_names = ", ".join(action.name for action in manifest.actions) or "None"
        self.add_row(Adw.ActionRow(title="Actions", subtitle=action_names))

        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.add_suffix(button_box)

        restart_button = Gtk.Button(icon_name="view-refresh-symbolic", tooltip_text="Restart", valign=Gtk.Align.CENTER)
        restart_button.connect("clicked", self.on_restart_clicked)
        button_box.append(restart_button)

        uninstall_button = Gtk.Button(
            icon_name="user-trash-symbolic",
            tooltip_text="Uninstall",
            css_classes=["destructive-action"],
            valign=Gtk.Align.CENTER,
        )
        uninstall_button.connect("clicked", self.on_uninstall_clicked)
        button_box.append(uninstall_button)

    def on_restart_clicked(self, button) -> None:
        gl.sd_sdk_manager.restart_plugin(self.manifest.uuid)
        plugin = gl.sd_sdk_manager.plugins.get(self.manifest.uuid)
        self.status_row.set_subtitle(plugin.get_status_text() if plugin else "Not loaded")

    def on_uninstall_clicked(self, button) -> None:
        dialog = ConfirmationDialog(
            title="Uninstall?",
            body=f'Are you sure you want to uninstall "{self.manifest.name}"? '
                 "Actions using it will stop working.",
            confirm="Uninstall",
            transient_for=self.group.page.get_root(),
            on_confirm=self.uninstall,
        )
        dialog.show()

    def uninstall(self) -> None:
        gl.sd_sdk_manager.uninstall(self.manifest.uuid)
        self.group.page.reload()


class _RequirementRow(Adw.ActionRow):
    """Shows whether an optional external interpreter is reachable."""

    def __init__(self, title: str, subtitle: str, command: str):
        super().__init__(title=title, subtitle=subtitle)
        self.command = command

        self.status_label = Gtk.Label(label="Checking…", css_classes=["dim-label"], valign=Gtk.Align.CENTER)
        self.add_suffix(self.status_label)

        threading.Thread(target=self._check, name=f"check_{command}", daemon=True).start()

    def _check(self) -> None:
        from src.backend.PluginManager.StreamDeckSDK.PluginProcess import _host_command_available
        available = _host_command_available(self.command)
        GLib.idle_add(self._set_result, available)

    def _set_result(self, available: bool) -> bool:
        self.status_label.set_label("Available" if available else "Not found")
        self.status_label.set_css_classes(["success"] if available else ["dim-label"])
        return False


class _NodeRow(Adw.ActionRow):
    """Node.js gets its own row because the version matters and the binary moves around."""

    def __init__(self):
        super().__init__(
            title="Node.js",
            subtitle="Needed by plugins whose code path is a JavaScript file, which is most modern ones",
        )
        self.status_label = Gtk.Label(label="Checking…", css_classes=["dim-label"], valign=Gtk.Align.CENTER)
        self.add_suffix(self.status_label)

        threading.Thread(target=self._check, name="check_node", daemon=True).start()

    def _check(self) -> None:
        from src.backend.PluginManager.StreamDeckSDK.PluginProcess import MINIMUM_NODE_VERSION, find_node
        command, found = find_node()
        if command is not None:
            result = (f"{command} ({found})", True)
        elif found is not None:
            result = (f"Version {found} is too old, need {MINIMUM_NODE_VERSION}+", False)
        else:
            result = ("Not found", False)
        GLib.idle_add(self._set_result, *result)

    def _set_result(self, text: str, available: bool) -> bool:
        self.status_label.set_label(text)
        self.status_label.set_css_classes(["success"] if available else ["dim-label"])
        return False


class _WebKitRow(Adw.ActionRow):
    def __init__(self):
        available = webkit_is_available()
        super().__init__(
            title="WebKitGTK",
            subtitle="Needed to show the settings interfaces (property inspectors) of plugins",
        )
        label = Gtk.Label(
            label="Available" if available else "Not found",
            css_classes=["success"] if available else ["dim-label"],
            valign=Gtk.Align.CENTER,
        )
        self.add_suffix(label)
