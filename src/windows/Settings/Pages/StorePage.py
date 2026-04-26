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
from GtkHelper.GtkHelper import BetterPreferencesGroup

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk

if TYPE_CHECKING:
    from src.windows.Settings.Settings import Settings


class StorePage(Adw.PreferencesPage):
    def __init__(self, settings: "Settings"):
        self.settings = settings
        super().__init__()
        self.set_title(gl.lm.get("settings-store-settings-title"))
        self.set_icon_name("go-home-symbolic")

        self.add(StorePageGroup(settings=settings))

class StorePageGroup(Adw.PreferencesGroup):
    def __init__(self, settings: "Settings"):
        self.settings = settings
        super().__init__(title=gl.lm.get("settings-store-settings-header"))

        self.auto_update = Adw.SwitchRow(title=gl.lm.get("settings-store-settings-auto-update"), active=True)
        self.add(self.auto_update)

        self.custom_stores = CustomContentGroup(title=gl.lm.get("settings-store-custom-stores-header"),
                                                description=gl.lm.get("settings-store-custom-stores-subtitle"),
                                                custom_type="stores", margin_top=12)
        self.add(self.custom_stores)

        self.custom_plugins = CustomContentGroup(title=gl.lm.get("settings-store-custom-plugins-header"),
                                                 description=gl.lm.get("settings-store-custom-plugins-subtitle"),
                                                 custom_type="plugins", margin_top=12)
        self.add(self.custom_plugins)

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

class CustomContentGroup(BetterPreferencesGroup):
    def __init__(self, title: str, description: str,custom_type: str, **kwargs):
        super().__init__(title=title, description=description, **kwargs)

        self.custom_type = custom_type
        self.enable_key = f"enable-custom-{self.custom_type}"
        self.store_key = f"custom-{self.custom_type}"

        self.suffix_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.set_header_suffix(self.suffix_box)
        
        self.enable_switch = Gtk.Switch(valign=Gtk.Align.CENTER)
        self.enable_switch.connect("state-set", self.on_toggle_enable)
        self.suffix_box.append(self.enable_switch)

        self.add_button = Gtk.Button(icon_name="list-add-symbolic", css_classes=["flat"])
        self.add_button.connect("clicked", self.on_add_button_clicked)
        self.suffix_box.append(self.add_button)

        self.load_config_values()

    def on_toggle_enable(self, switch: Gtk.Switch, *args):
        settings = gl.settings_manager.get_app_settings()
        settings.setdefault("store", {})
        settings["store"][self.enable_key] = switch.get_active()

        gl.settings_manager.save_app_settings(settings)

    def add_row(self, i: int, url: str, branch: str):
        self.add(CustomContentEntry(content_group=self, i=i, url=url, branch=branch))

    def load_config_values(self):
        settings = gl.settings_manager.get_app_settings()

        self.enable_switch.set_active(settings.get("store", {}).get(self.enable_key, False))

        for i, entry in enumerate(settings.get("store", {}).get(self.store_key, [])):
            self.add_row(i, entry.get("url", ""), entry.get("branch", ""))

    def on_add_button_clicked(self, *args):
        settings = gl.settings_manager.get_app_settings()

        settings.setdefault("store", {})
        settings["store"].setdefault(self.store_key, [])
        settings["store"][self.store_key].append({"url": None, "branch": None})

        self.add_row(len(settings["store"][self.store_key]) - 1, None, None)

        gl.settings_manager.save_app_settings(settings)

    def update_indicies(self):
        for i, row in enumerate(self.get_rows()):
            row.i = i

class CustomContentEntry(Adw.PreferencesRow):
    def __init__(self, content_group: CustomContentGroup, i: int, url: str, branch: str):
        super().__init__(activatable=False)

        self.content_group = content_group
        self.i = i
        self.url = url
        self.branch = branch

        self.main_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5, margin_start=5, margin_end=5)
        self.set_child(self.main_box)

        self.entry_grid = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, homogeneous=True)
        self.main_box.append(self.entry_grid)

        self.url = Adw.EntryRow(title="Repository URL", valign=Gtk.Align.CENTER, text=url or "")
        self.url.connect("changed", self.on_value_changed)
        self.entry_grid.append(self.url)

        self.branch = Adw.EntryRow(title="Branch", valign=Gtk.Align.CENTER, text=branch or "")
        self.branch.connect("changed", self.on_value_changed)
        self.entry_grid.append(self.branch)

        self.button_remove = Gtk.Button(icon_name="user-trash-symbolic", valign=Gtk.Align.CENTER, css_classes=["destructive-action-on-hover", "flat"])
        self.main_box.append(self.button_remove)

        self.button_remove.connect("clicked", self.on_remove)

    def on_value_changed(self, *args):
        settings = gl.settings_manager.get_app_settings()

        settings.setdefault("store", {})
        settings["store"].setdefault(self.content_group.store_key, [])
        settings["store"][self.content_group.store_key][self.i]["url"] = self.url.get_text()
        settings["store"][self.content_group.store_key][self.i]["branch"] = self.branch.get_text()

        gl.settings_manager.save_app_settings(settings)

    def on_remove(self, *args):
        self.content_group.remove(self)

        settings = gl.settings_manager.get_app_settings()
        stores = settings.get("store", {}).get(self.content_group.store_key, [])
        if self.i < len(stores):
            stores.pop(self.i)

        settings.setdefault("store", {})
        settings["store"][self.content_group.store_key] = stores

        gl.settings_manager.save_app_settings(settings)

        self.content_group.update_indicies()
