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
from typing import TYPE_CHECKING

import gi

import globals as gl

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw

if TYPE_CHECKING:
    from src.windows.Settings.Settings import Settings


class UIPage(Adw.PreferencesPage):
    def __init__(self, settings: "Settings"):
        super().__init__()
        self.settings = settings
        self.set_title(gl.lm.get("settings-ui-settings-title"))
        self.set_icon_name("window-new-symbolic")

        self.add(UIPageGroup(settings=settings))

class UIPageGroup(Adw.PreferencesGroup):
    def __init__(self, settings: "Settings"):
        self.settings = settings
        super().__init__(title=gl.lm.get("settings-ui-settings-key-grid-header"))

        self.trayicon_row = Adw.SwitchRow(title=gl.lm.get("settings-show-tray-icon"), active=True)
        self.add(self.trayicon_row)

        self.emulate_row = Adw.SwitchRow(title=gl.lm.get("settings-emulate-at-double-click"), active=True)
        self.add(self.emulate_row)

        self.enable_fps_warnings_row = Adw.SwitchRow(title=gl.lm.get("settings.enable-fps-warnings"), active=True)
        self.add(self.enable_fps_warnings_row)

        self.allow_white_mode = Adw.SwitchRow(title=gl.lm.get("settings-allow-white-mode"), subtitle=gl.lm.get("settings-allow-white-mode-subtitle"), active=False)
        self.add(self.allow_white_mode)

        self.show_notifications = Adw.SwitchRow(title=gl.lm.get("settings-show-notifications"), subtitle=gl.lm.get("settings-show-notifications-subtitle"), active=True)
        self.add(self.show_notifications)

        self.auto_config_row = Adw.SwitchRow(title=gl.lm.get("settings-auto-open-action-config"), subtitle=gl.lm.get("settings-auto-open-action-config-subtitle"), active=True)
        self.add(self.auto_config_row)

        self.load_defaults()

        # Connect signals
        self.trayicon_row.connect("notify::active", self.on_trayicon_row_toggled)
        self.emulate_row.connect("notify::active", self.on_emulate_row_toggled)
        self.enable_fps_warnings_row.connect("notify::active", self.on_enable_fps_warnings_row_toggled)
        self.allow_white_mode.connect("notify::active", self.on_allow_white_mode_toggled)
        self.show_notifications.connect("notify::active", self.on_show_notifications_toggled)
        self.auto_config_row.connect("notify::active", self.on_auto_config_row_toggled)

    def load_defaults(self):
        self.trayicon_row.set_active(self.settings.settings_json.get("ui",{}).get("tray-icon", True))
        self.emulate_row.set_active(self.settings.settings_json.get("key-grid", {}).get("emulate-at-double-click", True))
        self.enable_fps_warnings_row.set_active(self.settings.settings_json.get("warnings", {}).get("enable-fps-warnings", True))
        self.allow_white_mode.set_active(self.settings.settings_json.get("ui", {}).get("allow-white-mode", False))
        self.show_notifications.set_active(self.settings.settings_json.get("ui", {}).get("show-notifications", True))
        self.auto_config_row.set_active(self.settings.settings_json.get("ui", {}).get("auto-open-action-config", True))


    def on_trayicon_row_toggled(self, *args):
        self.settings.settings_json.setdefault("ui", {})
        self.settings.settings_json["ui"]["tray-icon"] = self.trayicon_row.get_active()

        self.settings.save_json()
        if self.settings.settings_json["ui"]["tray-icon"]:
            gl.tray_icon.start()
        else:
            gl.tray_icon.stop()

    def on_emulate_row_toggled(self, *args):
        self.settings.settings_json.setdefault("key-grid", {})
        self.settings.settings_json["key-grid"]["emulate-at-double-click"] = self.emulate_row.get_active()

        # Save
        self.settings.save_json()

    def on_enable_fps_warnings_row_toggled(self, *args):
        self.settings.settings_json.setdefault("warnings", {})
        self.settings.settings_json["warnings"]["enable-fps-warnings"] = self.enable_fps_warnings_row.get_active()

        # Save
        self.settings.save_json()

        # Inform all deck controllers
        for controller in gl.deck_manager.deck_controller:
            controller.media_player.set_show_fps_warnings(self.enable_fps_warnings_row.get_active())

    def on_allow_white_mode_toggled(self, *args):
        self.settings.settings_json.setdefault("ui", {})
        self.settings.settings_json["ui"]["allow-white-mode"] = self.allow_white_mode.get_active()

        if self.allow_white_mode.get_active():
            gl.app.style_manager.set_color_scheme(Adw.ColorScheme.PREFER_DARK)
        else:
            gl.app.style_manager.set_color_scheme(Adw.ColorScheme.FORCE_DARK)

        # Save
        self.settings.save_json()

    def on_show_notifications_toggled(self, *args):
        self.settings.settings_json.setdefault("ui", {})
        self.settings.settings_json["ui"]["show-notifications"] = self.show_notifications.get_active()

        # Save
        self.settings.save_json()

    def on_auto_config_row_toggled(self, *args):
        self.settings.settings_json.setdefault("ui", {})
        self.settings.settings_json["ui"]["auto-open-action-config"] = self.auto_config_row.get_active()

        # Save
        self.settings.save_json()
