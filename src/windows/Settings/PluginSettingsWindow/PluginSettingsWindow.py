"""
Author: Core447
Year: 2024

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
any later version.

This programm comes with ABSOLUTELY NO WARRANTY!

You should have received a copy of the GNU General Public License
along with this program. If not, see <https://www.gnu.org/licenses/>.
"""

import gi
from gi.repository import Gtk, Adw

from src.backend.PluginManager.PluginBase import PluginBase
import globals as gl

class PluginSettingsWindow(Adw.PreferencesDialog):
    def __init__(self, plugin_base: PluginBase):
        super().__init__(title=f"{plugin_base.plugin_name} Settings")

        self.settings_page = SettingsPage(self, plugin_base)
        self.assets_page = AssetsPage(self, plugin_base)
        self.color_page = ColorPage(self, plugin_base)

        self.add(self.settings_page)
        self.add(self.assets_page)
        self.add(self.color_page)


class SettingsPage(Adw.PreferencesPage):
    def __init__(self, settings_window: PluginSettingsWindow, plugin_base: PluginBase):
        super().__init__(title="Settings", icon_name="preferences-system-symbolic")
        self.settings_window = settings_window

class AssetsPage(Adw.PreferencesPage):
    def __init__(self, settings_window: PluginSettingsWindow, plugin_base: PluginBase):
        super().__init__(title="Assets", icon_name="image-x-generic-symbolic")
        self.settings_window = settings_window

class ColorPage(Adw.PreferencesPage):
    def __init__(self, settings_window: PluginSettingsWindow, plugin_base: PluginBase):
        super().__init__(title="Colors", icon_name="color-select-symbolic")
        self.settings_window = settings_window