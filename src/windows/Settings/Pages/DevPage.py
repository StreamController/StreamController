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
import subprocess
from typing import TYPE_CHECKING

import gi

import globals as gl
from autostart import is_flatpak

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk

if TYPE_CHECKING:
    from src.windows.Settings.Settings import Settings


class DevPage(Adw.PreferencesPage):
    def __init__(self, settings: "Settings"):
        self.settings = settings
        super().__init__()
        self.set_title(gl.lm.get("settings-dev-settings-title"))
        self.set_icon_name("text-editor-symbolic")

        self.add(FakeDecksGroup(settings=settings))
        self.add(RemoteDecksGroup(settings=settings))
        self.add(DataPathGroup(settings=settings))

class FakeDecksGroup(Adw.PreferencesGroup):
    def __init__(self, settings: "Settings"):
        self.settings = settings
        super().__init__(title=gl.lm.get("settings-fake-decks-header"))

        self.n_fake_decks_row = Adw.SpinRow.new_with_range(min=0, max=3, step=1)
        self.n_fake_decks_row.set_title(gl.lm.get("settings-number-of-fake-decks"))
        self.n_fake_decks_row.set_subtitle(gl.lm.get("settings-number-of-fake-decks-hint"))
        self.n_fake_decks_row.set_range(0, 3)
        self.add(self.n_fake_decks_row)

        self.load_defaults()

        # Connect signals
        self.n_fake_decks_row.connect("changed", self.on_n_fake_decks_row_changed)

    def load_defaults(self):
        self.n_fake_decks_row.set_value(self.settings.settings_json.get("dev", {}).get("n-fake-decks", 0))

    def on_n_fake_decks_row_changed(self, *args):
        #FIXME: For some reason this gets called twice
        self.settings.settings_json.setdefault("dev", {})
        self.settings.settings_json["dev"]["n-fake-decks"] = self.n_fake_decks_row.get_value()

        # Save
        self.settings.save_json()

        # Reload decks
        gl.deck_manager.load_fake_decks()


class RemoteDecksGroup(Adw.PreferencesGroup):
    def __init__(self, settings: "Settings"):
        self.settings = settings
        super().__init__(title="Remote Decks")

        self.n_remote_decks_row = Adw.SpinRow.new_with_range(min=0, max=1, step=1)
        self.n_remote_decks_row.set_title("Number of remote decks")
        self.n_remote_decks_row.set_subtitle("Use remote.sc.core447.com to connect (beta)")
        self.n_remote_decks_row.set_range(0, 1)
        self.add(self.n_remote_decks_row)

        self.load_defaults()

        # Connect signals
        self.n_remote_decks_row.connect("changed", self.on_row_changed)

    def load_defaults(self):
        n_decks = gl.settings_manager.get_app_settings().get("dev", {}).get("n-remote-decks", 0)
        self.n_remote_decks_row.set_value(n_decks)

    def on_row_changed(self, *args):
        #FIXME: For some reason this gets called twice
        n_decks = self.n_remote_decks_row.get_value()
        app_settings = gl.settings_manager.get_app_settings() 
        print(app_settings)


        app_settings.setdefault("dev", {})
        app_settings["dev"]["n-remote-decks"] = n_decks

        # Save
        gl.settings_manager.save_app_settings(app_settings)

        if n_decks > 0:
            gl.deck_manager.load_remote_decks()
        else:
            gl.deck_manager.remove_remote_decks()


class DataPathGroup(Adw.PreferencesGroup):
    def __init__(self, settings: "Settings"):
        self.settings = settings
        super().__init__(title="Data path")

        self.data_path = Adw.EntryRow(title="Data path (requires restart)")
        self.add(self.data_path)

        self.open_data_path_button = Gtk.Button(label="Open", valign=Gtk.Align.CENTER)
        self.open_data_path_button.connect("clicked", self.on_open_data_path_button_clicked)
        self.data_path.add_suffix(self.open_data_path_button)

        self.load_defaults()

        # Connect signals
        self.data_path.connect("notify::text", self.on_data_path_changed)

    def load_defaults(self):
        static_settings = gl.settings_manager.get_static_settings()
        self.data_path.set_text(static_settings.get("data-path", gl.DATA_PATH))

    def on_data_path_changed(self, *args):
        static_settings = gl.settings_manager.get_static_settings()
        static_settings["data-path"] = self.data_path.get_text()
        gl.settings_manager.save_static_settings(static_settings)

    def on_open_data_path_button_clicked(self, *args):
        command = ""
        if is_flatpak():
            command += "flatpak-spawn --host "

        command += f"xdg-open {self.data_path.get_text()}"

        try:
            subprocess.check_output(command, shell=True)
        except subprocess.CalledProcessError:
            pass
