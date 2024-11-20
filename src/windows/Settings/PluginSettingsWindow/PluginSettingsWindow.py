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
from gi.repository import Gtk, Adw, Gio

from GtkHelper.GtkHelper import better_disconnect
from src.backend.PluginManager.PluginBase import PluginBase
from src.backend.PluginManager.AssetManagment.PluginAssetManager import Icon, Color
from .PluginAssetPreview import IconPreview, ColorPreview

class PluginSettingsWindow(Adw.PreferencesDialog):
    def __init__(self, plugin_base: PluginBase):
        super().__init__(title=f"{plugin_base.plugin_name} Settings")

        self.set_size_request(500, 500)

        self.settings_page = SettingsPage(self, plugin_base)
        self.assets_page = AssetsPage(self, plugin_base)
        self.color_page = ColorPage(self, plugin_base)

        self.add(self.settings_page)
        self.add(self.assets_page)
        self.add(self.color_page)

class PluginSettingsPage(Adw.PreferencesPage):
    def __init__(self, settings_window: PluginSettingsWindow, plugin_base: PluginBase, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.settings_window = settings_window
        self.plugin_base = plugin_base

        self.build()

    def build(self):
        group = Adw.PreferencesGroup()
        self.add(group)

        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        group.add(main_box)

        search_entry = Gtk.SearchEntry()
        search_entry.set_placeholder_text("Search Asset...")
        main_box.append(search_entry)

        scrolled_window = Gtk.ScrolledWindow(hexpand=True, vexpand=True)
        group.add(scrolled_window)

        self.flow_box = Gtk.FlowBox(hexpand=True, orientation=Gtk.Orientation.HORIZONTAL,
                               selection_mode=Gtk.SelectionMode.SINGLE, valign=Gtk.Align.START)
        self.flow_box.set_max_children_per_line(3)
        self.flow_box.set_row_spacing(5)
        self.flow_box.set_column_spacing(5)

        scrolled_window.set_child(self.flow_box)

    def connect_flow_box(self, callback: callable):
        self.flow_box.connect("child-activated", callback)

    def disconnect_flow_box(self,callback: callable):
        better_disconnect(self.flow_box, callback)

    def reset_button_clicked(self, *args):
        pass

class SettingsPage(Adw.PreferencesPage):
    def __init__(self, settings_window: PluginSettingsWindow, plugin_base: PluginBase):
        super().__init__(title="Settings", icon_name="preferences-system-symbolic")
        self.settings_window = settings_window
        self.plugin_base = plugin_base
        self.build()

    def build(self):
        area = self.plugin_base.get_settings_area()
        if area:
            self.add(area)

class AssetsPage(PluginSettingsPage):
    def __init__(self, *args, **kwargs):
        super().__init__(title="Assets", icon_name="image-x-generic-symbolic", *args, **kwargs)
        self.display_icons()
        self.connect_flow_box(self.on_icon_clicked)

    def on_icon_clicked(self, flow_box, preview: IconPreview):
        icon_dialog = Gtk.FileDialog.new()
        icon_dialog.set_title("Icon")

        icon_dialog.open(None, None, self.on_icon_dialog_response, preview)

    def on_icon_dialog_response(self, dialog: Gtk.FileDialog, task, preview: IconPreview):
        file = dialog.open_finish(task)

        if file:
            file_path = file.get_path()
            self.plugin_base.asset_manager.icons.add_override(preview.name, Icon(path=file_path), override=True)

            _, render = self.plugin_base.asset_manager.icons.get_asset_values(preview.name)
            preview.set_image(render)
            self.plugin_base.asset_manager.save_assets()

    def display_icons(self):
        icons = self.plugin_base.asset_manager.icons.get_assets_merged()

        for name, icon in icons.items():
            _, render = icon.get_values()

            preview = IconPreview(window=self, name=name, image=render, size=(100, 100), vexpand=False, hexpand=False)
            self.flow_box.append(preview)

    def reset_button_clicked(self, *args):
        preview = args[1]
        if type(preview) == IconPreview:
            self.plugin_base.asset_manager.icons.remove_override(preview.name)
            _, render = self.plugin_base.asset_manager.icons.get_asset(preview.name).get_values()
            preview.set_image(render)
            self.plugin_base.asset_manager.save_assets()

class ColorPage(PluginSettingsPage):
    def __init__(self, *args, **kwargs):
        super().__init__(title="Colors", icon_name="color-select-symbolic", *args, **kwargs)
        self.display_colors()
        self.connect_flow_box(self.on_color_clicked)

    def on_color_clicked(self, flow_box, preview: ColorPreview):
        color_dialog = Gtk.ColorDialog.new()
        color_dialog.set_title("Color")

        # Open the dialog
        color_dialog.choose_rgba(None, preview.get_rgba(), None, self.on_color_dialog_response, preview)

    def on_color_dialog_response(self, dialog: Gtk.ColorDialog, task: Gio.Task, preview: ColorPreview):
        rgba = dialog.choose_rgba_finish(task)
        preview.set_color_rgba(rgba)
        self.plugin_base.asset_manager.colors.add_override(preview.name, Color(color=preview.color), override=True)
        self.plugin_base.asset_manager.save_assets()

    def display_colors(self):
        colors = self.plugin_base.asset_manager.colors.get_assets_merged()

        for name, color in colors.items():
            color = color.get_values()
            preview = ColorPreview(window=self, name=name, color=color, size=(100, 100), hexpand=False, vexpand=False)
            self.flow_box.append(preview)

    def reset_button_clicked(self, *args):
        preview = args[1]
        if type(preview) == ColorPreview:
            self.plugin_base.asset_manager.colors.remove_override(preview.name)
            preview.set_color(self.plugin_base.asset_manager.colors.get_asset(preview.name).get_values())
            self.plugin_base.asset_manager.save_assets()