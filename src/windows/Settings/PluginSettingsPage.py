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
from src.windows.Settings import Settings

import globals as gl
from .PluginSettingsWindow.PluginSettingsWindow import PluginSettingsWindow
from .PluginAbout import PluginAboutFactory


class PluginSettingsPage(Adw.PreferencesPage):
    def __init__(self, settings: Settings):
        super().__init__()
        self.settings = settings
        self.set_title("Plugins")
        self.set_icon_name("application-x-addon-symbolic")

        self.add(PluginSettingsGroup(plugin_page=self))

class PluginSettingsGroup(Adw.PreferencesGroup):
    def __init__(self, plugin_page: PluginSettingsPage):
        super().__init__(title="Plugin Settings")
        for plugin_id in gl.plugin_manager.get_plugins():
            plugin_base = gl.plugin_manager.get_plugin_by_id(plugin_id)
            self.add(PluginRow(plugin_page=plugin_page, plugin_base=plugin_base))

class IconTextButton(Gtk.Button):
    def __init__(self, icon_name: str, text: str, **kwargs):
        super().__init__(**kwargs)
        self.box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        self.set_child(self.box)

        self.box.append(Gtk.Image(icon_name=icon_name, margin_end=5))
        self.box.append(Gtk.Label(label=text))

class PluginRow(Adw.ActionRow):
    def __init__(self, plugin_page: PluginSettingsPage, plugin_base: PluginBase):
        self.plugin_page = plugin_page
        self.plugin_base = plugin_base
        super().__init__(title=plugin_base.plugin_name, subtitle=plugin_base.plugin_id)

        self.suffix_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.add_suffix(self.suffix_box)

        self.settings_window_button = IconTextButton(icon_name="emblem-system-symbolic", text="Settings", valign=Gtk.Align.CENTER)
        self.suffix_box.append(self.settings_window_button)

        self.changelog_window_button = IconTextButton(icon_name="help-about-symbolic", text="About", valign=Gtk.Align.CENTER)
        self.suffix_box.append(self.changelog_window_button)

        self.troubleshoot_button = IconTextButton(icon_name="system-run-symbolic", text="Diagnostics", valign=Gtk.Align.CENTER)
        self.suffix_box.append(self.troubleshoot_button)

        self.settings_window_button.connect("clicked", self.on_settings_window_button_clicked)
        self.changelog_window_button.connect("clicked", self.on_changelog_window_button_clicked)
        self.troubleshoot_button.connect("clicked", self.on_troubleshoot_button_clicked)

    def on_settings_window_button_clicked(self, *args):
        settings = PluginSettingsWindow(self.plugin_base)
        settings.present(self.plugin_page.settings)

    def on_changelog_window_button_clicked(self, *args):
        factory = PluginAboutFactory(self.plugin_base)
        about = factory.create_new_about()

        about.present(self)

    def on_troubleshoot_button_clicked(self, *args):
        self.plugin_base.troubleshoot()

class ToggleRow(Adw.ActionRow):
    def __init__(self):
        super().__init__()
        self.set_title("Test setting")
        self.set_subtitle("Test setting description")
        self.add_suffix(Gtk.Switch(valign=Gtk.Align.CENTER))
