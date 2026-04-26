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
from autostart import setup_autostart

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw

if TYPE_CHECKING:
    from src.windows.Settings.Settings import Settings


class SystemPage(Adw.PreferencesPage):
    def __init__(self, settings: "Settings"):
        self.settings = settings
        super().__init__()
        self.set_title(gl.lm.get("settings-system-settings-title"))
        self.set_icon_name("system-run-symbolic")

        self.add(SystemGroup(settings=settings))

class SystemGroup(Adw.PreferencesGroup):
    def __init__(self, settings: "Settings"):
        self.settings = settings
        super().__init__(title=gl.lm.get("settings-system-settings-header"))

        self.keep_running = Adw.SwitchRow(title=gl.lm.get("settings-system-settings-keep-running"), subtitle=gl.lm.get("settings-system-settings-keep-running-subtitle"), active=False)
        self.add(self.keep_running)

        self.autostart = Adw.SwitchRow(title=gl.lm.get("settings-system-settings-autostart"), subtitle=gl.lm.get("settings-system-settings-autostart-subtitle"), active=True)
        self.add(self.autostart)

        self.lock_on_lock_screen = Adw.SwitchRow(title="Lock decks when screen is locked", subtitle="Works on Gnome, KDE, Cinnamon and Hyprland", active=True)
        self.add(self.lock_on_lock_screen)

        self.beta_resume_mode = Adw.SwitchRow(title="Use new resume mode (beta)", subtitle="Use new way to resume after suspends - requires restart", active=False)
        self.add(self.beta_resume_mode)

        self.load_defaults()

        # Connect signals
        self.keep_running.connect("notify::active", self.on_keep_running_toggled)
        self.autostart.connect("notify::active", self.on_autostart_toggled)
        self.lock_on_lock_screen.connect("notify::active", self.on_lock_on_lock_screen_toggled)
        self.beta_resume_mode.connect("notify::active", self.on_beta_resume_mode_toggled)

    def load_defaults(self):
        self.keep_running.set_active(self.settings.settings_json.get("system", {}).get("keep-running", False) == True)
        self.autostart.set_active(self.settings.settings_json.get("system", {}).get("autostart", True))
        self.lock_on_lock_screen.set_active(self.settings.settings_json.get("system", {}).get("lock-on-lock-screen", True))
        self.beta_resume_mode.set_active(self.settings.settings_json.get("system", {}).get("beta-resume-mode", True))

    def on_keep_running_toggled(self, *args):
        self.settings.settings_json.setdefault("system", {})
        self.settings.settings_json["system"]["keep-running"] = self.keep_running.get_active()

        # Save
        self.settings.save_json()

    def on_autostart_toggled(self, *args):
        self.settings.settings_json.setdefault("system", {})
        self.settings.settings_json["system"]["autostart"] = self.autostart.get_active()

        setup_autostart(self.autostart.get_active())

        # Save
        self.settings.save_json()

    def on_lock_on_lock_screen_toggled(self, *args):
        self.settings.settings_json.setdefault("system", {})
        self.settings.settings_json["system"]["lock-on-lock-screen"] = self.lock_on_lock_screen.get_active()

        # Save
        self.settings.save_json()

    def on_beta_resume_mode_toggled(self, *args):
        self.settings.settings_json.setdefault("system", {})
        self.settings.settings_json["system"]["beta-resume-mode"] = self.beta_resume_mode.get_active()

        # Save
        self.settings.save_json()
