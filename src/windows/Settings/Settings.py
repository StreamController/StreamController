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

class Settings(Adw.PreferencesWindow):
    def __init__(self):
        super().__init__(title="Settings")
        self.set_default_size(800, 600)

        self.add(UIPage())
        self.add(StorePage())
        self.add(DevPage())


class UIPage(Adw.PreferencesPage):
    def __init__(self):
        super().__init__()
        self.set_title("UI Settings")
        self.set_icon_name("system-run-symbolic")

        self.add(UIPageGroup())

class UIPageGroup(Adw.PreferencesGroup):
    def __init__(self):
        super().__init__(title="Key Grid")

        self.emulate_row = Adw.SwitchRow(title="Emulate button press on double click", active=True)
        self.add(self.emulate_row)


class DevPage(Adw.PreferencesPage):
    def __init__(self):
        super().__init__()
        self.set_title("Developer Settings")
        self.set_icon_name("code-block")

        self.add(DevPageGroup())

class DevPageGroup(Adw.PreferencesGroup):
    def __init__(self):
        super().__init__(title="Fake Decks")

        self.n_fake_decks_row = Adw.SpinRow.new_with_range(min=0, max=3, step=1)
        self.n_fake_decks_row.set_title("Number of fake decks")
        self.n_fake_decks_row.set_subtitle("For testing purposes")
        self.n_fake_decks_row.set_range(0, 3)
        self.add(self.n_fake_decks_row)

class StorePage(Adw.PreferencesPage):
    def __init__(self):
        super().__init__()
        self.set_title("Store")
        self.set_icon_name("download-symbolic")

        self.add(StorePageGroup())        

class StorePageGroup(Adw.PreferencesGroup):
    def __init__(self):
        super().__init__(title="Store")

        self.auto_update = Adw.SwitchRow(title="Auto update assets", active=True)
        self.add(self.auto_update)