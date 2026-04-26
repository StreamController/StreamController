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
import os

import gi

import globals as gl
from src.windows.Settings.Pages.DevPage import DevPage
from src.windows.Settings.Pages.GeneralPage import GeneralPage
from src.windows.Settings.Pages.PerformancePage import PerformancePage
from src.windows.Settings.Pages.StorePage import StorePage
from src.windows.Settings.Pages.SystemPage import SystemPage
from src.windows.Settings.Pages.UIPage import UIPage
from src.windows.Settings.PluginSettingsPage import PluginSettingsPage

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw


class Settings(Adw.PreferencesWindow):
    def __init__(self):
        super().__init__(title="Settings")
        self.set_default_size(1000, 700)

        # Center settings win over main_win (depends on DE)
        self.set_transient_for(gl.app.main_win)
        # Allow interaction with other windows
        self.set_modal(True)

        self.settings_json:dict = None
        self.load_json()

        self.general_page = GeneralPage(settings=self)
        self.ui_page = UIPage(settings=self)
        self.store_page = StorePage(settings=self)
        self.performance_page = PerformancePage(settings=self)
        self.dev_page = DevPage(settings=self)
        self.system_page = SystemPage(settings=self)
        self.plugin_page = PluginSettingsPage(settings=self)

        self.add(self.general_page)
        self.add(self.ui_page)
        self.add(self.store_page)
        self.add(self.performance_page)
        self.add(self.system_page)
        self.add(self.dev_page)
        self.add(self.plugin_page)

    def load_json(self):
        # Load settings from file
        settings = gl.settings_manager.load_settings_from_file(os.path.join(gl.DATA_PATH, "settings", "settings.json"))
        self.settings_json = settings
    
    def save_json(self):
        gl.settings_manager.save_settings_to_file(os.path.join(gl.DATA_PATH, "settings", "settings.json"), self.settings_json)
