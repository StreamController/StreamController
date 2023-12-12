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
# Import gtk modules
import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, Gio

# Import globals
import globals as gl

class Settings(Adw.PreferencesWindow):
    def __init__(self):
        super().__init__(title="Settings")
        self.set_default_size(800, 600)

        self.settings_json:dict = None
        self.load_json()

        self.add(UIPage(settings=self))
        self.add(StorePage(settings=self))
        self.add(DevPage(settings=self))

    def load_json(self):
        # Load settings from file
        settings = gl.settings_manager.load_settings_from_file("settings.json")
        self.settings_json = settings
    
    def save_json(self):
        gl.settings_manager.save_settings_to_file("settings.json", self.settings_json)


class UIPage(Adw.PreferencesPage):
    def __init__(self, settings: Settings):
        super().__init__()
        self.settings = settings
        self.set_title("UI Settings")
        self.set_icon_name("system-run-symbolic")

        self.add(UIPageGroup(settings=settings))

class UIPageGroup(Adw.PreferencesGroup):
    def __init__(self, settings: Settings):
        self.settings = settings
        super().__init__(title="Key Grid")

        self.emulate_row = Adw.SwitchRow(title="Emulate button press on double click", active=True)
        self.add(self.emulate_row)

        self.load_defaults()

        # Connect signals
        self.emulate_row.connect("notify::active", self.on_emulate_row_toggled)

    def load_defaults(self):
        self.emulate_row.set_active(self.settings.settings_json.get("key-grid", {}).get("emulate-at-double-click", True))

    def on_emulate_row_toggled(self, *args):
        self.settings.settings_json.setdefault("key-grid", {})
        self.settings.settings_json["key-grid"]["emulate-at-double-click"] = self.emulate_row.get_active()

        # Save
        self.settings.save_json()


class DevPage(Adw.PreferencesPage):
    def __init__(self, settings: Settings):
        self.settings = settings
        super().__init__()
        self.set_title("Developer Settings")
        self.set_icon_name("code-block")

        self.add(DevPageGroup(settings=settings))

class DevPageGroup(Adw.PreferencesGroup):
    def __init__(self, settings: Settings):
        self.settings = settings
        super().__init__(title="Fake Decks")

        self.n_fake_decks_row = Adw.SpinRow.new_with_range(min=0, max=3, step=1)
        self.n_fake_decks_row.set_title("Number of fake decks")
        self.n_fake_decks_row.set_subtitle("For testing purposes")
        self.n_fake_decks_row.set_range(0, 3)
        self.add(self.n_fake_decks_row)

        self.load_defaults()

        # Connect signals
        self.n_fake_decks_row.connect("changed", self.on_n_fake_decks_row_changed)

    def load_defaults(self):
        self.n_fake_decks_row.set_value(self.settings.settings_json.get("dev", {}).get("n-fake-decks", 0))

    def on_n_fake_decks_row_changed(self, *args):
        self.settings.settings_json.setdefault("dev", {})
        self.settings.settings_json["dev"]["n-fake-decks"] = self.n_fake_decks_row.get_value()

        # Save
        self.settings.save_json()

class StorePage(Adw.PreferencesPage):
    def __init__(self, settings: Settings):
        self.settings = settings
        super().__init__()
        self.set_title("Store")
        self.set_icon_name("download-symbolic")

        self.add(StorePageGroup(settings=settings))

class StorePageGroup(Adw.PreferencesGroup):
    def __init__(self, settings: Settings):
        self.settings = settings
        super().__init__(title="Store")

        self.auto_update = Adw.SwitchRow(title="Auto update assets", active=True)
        self.add(self.auto_update)

        self.load_defaults()

        # Connect signals
        self.auto_update.connect("notify::active", self.on_auto_update_toggled)

    def load_defaults(self):
        self.auto_update.set_active(self.settings.settings_json.get("store", {}).get("auto-update", True))

    def on_auto_update_toggled(self, *args):
        self.settings.settings_json.setdefault("store", {})
        self.settings.settings_json["store"]["auto-update"] = self.auto_update.get_active()

        # Save
        self.settings.save_json()