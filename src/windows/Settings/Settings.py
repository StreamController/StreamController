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

from autostart import setup_autostart

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, Gio

# Import globals
import globals as gl

import os

class Settings(Adw.PreferencesWindow):
    def __init__(self):
        super().__init__(title="Settings")
        self.set_default_size(800, 600)

        # Center settings win over main_win (depends on DE)
        self.set_transient_for(gl.app.main_win)
        # Allow interaction with other windows
        self.set_modal(False)

        self.settings_json:dict = None
        self.load_json()

        self.ui_page = UIPage(settings=self)
        self.store_page = StorePage(settings=self)
        self.performance_page = PerformancePage(settings=self)
        self.dev_page = DevPage(settings=self)
        self.system_page = SystemPage(settings=self)

        self.add(self.ui_page)
        self.add(self.store_page)
        self.add(self.dev_page)
        self.add(self.performance_page)
        self.add(self.system_page)

    def load_json(self):
        # Load settings from file
        settings = gl.settings_manager.load_settings_from_file(os.path.join(gl.DATA_PATH, "settings", "settings.json"))
        self.settings_json = settings
    
    def save_json(self):
        gl.settings_manager.save_settings_to_file(os.path.join(gl.DATA_PATH, "settings", "settings.json"), self.settings_json)


class UIPage(Adw.PreferencesPage):
    def __init__(self, settings: Settings):
        super().__init__()
        self.settings = settings
        self.set_title(gl.lm.get("settings-ui-settings-title"))
        self.set_icon_name("window-new-symbolic")

        self.add(UIPageGroup(settings=settings))

class UIPageGroup(Adw.PreferencesGroup):
    def __init__(self, settings: Settings):
        self.settings = settings
        super().__init__(title=gl.lm.get("settings-ui-settings-key-grid-header"))

        self.emulate_row = Adw.SwitchRow(title=gl.lm.get("settings-emulate-at-double-click"), active=True)
        self.add(self.emulate_row)

        self.enable_fps_warnings_row = Adw.SwitchRow(title=gl.lm.get("settings.enable-fps-warnings"), active=True)
        self.add(self.enable_fps_warnings_row)

        self.allow_white_mode = Adw.SwitchRow(title=gl.lm.get("settings-allow-white-mode"), subtitle=gl.lm.get("settings-allow-white-mode-subtitle"), active=False)
        self.add(self.allow_white_mode)

        self.show_notifications = Adw.SwitchRow(title=gl.lm.get("settings-show-notifications"), subtitle=gl.lm.get("settings-show-notifications-subtitle"), active=True)
        self.add(self.show_notifications)

        self.load_defaults()

        # Connect signals
        self.emulate_row.connect("notify::active", self.on_emulate_row_toggled)
        self.enable_fps_warnings_row.connect("notify::active", self.on_enable_fps_warnings_row_toggled)
        self.allow_white_mode.connect("notify::active", self.on_allow_white_mode_toggled)
        self.show_notifications.connect("notify::active", self.on_show_notifications_toggled)

    def load_defaults(self):
        self.emulate_row.set_active(self.settings.settings_json.get("key-grid", {}).get("emulate-at-double-click", True))
        self.enable_fps_warnings_row.set_active(self.settings.settings_json.get("warnings", {}).get("enable-fps-warnings", True))
        self.allow_white_mode.set_active(self.settings.settings_json.get("ui", {}).get("allow-white-mode", False))
        self.show_notifications.set_active(self.settings.settings_json.get("ui", {}).get("show-notifications", True))

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


class DevPage(Adw.PreferencesPage):
    def __init__(self, settings: Settings):
        self.settings = settings
        super().__init__()
        self.set_title(gl.lm.get("settings-dev-settings-title"))
        self.set_icon_name("text-editor-symbolic")

        self.add(DevPageGroup(settings=settings))

class DevPageGroup(Adw.PreferencesGroup):
    def __init__(self, settings: Settings):
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

class StorePage(Adw.PreferencesPage):
    def __init__(self, settings: Settings):
        self.settings = settings
        super().__init__()
        self.set_title(gl.lm.get("settings-store-settings-title"))
        self.set_icon_name("go-home-symbolic")

        self.add(StorePageGroup(settings=settings))

class StorePageGroup(Adw.PreferencesGroup):
    def __init__(self, settings: Settings):
        self.settings = settings
        super().__init__(title=gl.lm.get("settings-store-settings-header"))

        self.auto_update = Adw.SwitchRow(title=gl.lm.get("settings-store-settings-auto-update"), active=True)
        self.add(self.auto_update)

        self.use_custom_stores = Adw.SwitchRow(title=gl.lm.get("settings-store-settings-custom-stores"), active=False)
        self.add(self.use_custom_stores)

        self.use_custom_plugins = Adw.SwitchRow(title=gl.lm.get("settings-store-settings-custom-plugins"), active=False)
        self.add(self.use_custom_plugins)

        self.custom_stores = CustomContentGroup(title=gl.lm.get("settings-store-custom-stores-header"))
        self.add(self.custom_stores)

        self.custom_plugins = CustomContentGroup(title=gl.lm.get("settings-store-custom-plugins-header"))
        self.add(self.custom_plugins)

        self.load_defaults()

        # Make Groups In-/Active
        self.custom_stores.set_sensitive(self.use_custom_stores.get_active())
        self.custom_plugins.set_sensitive(self.use_custom_plugins.get_active())

        # Connect signals
        self.auto_update.connect("notify::active", self.on_auto_update_toggled)
        self.use_custom_stores.connect("notify::active", self.on_use_custom_stores_toggled)
        self.use_custom_plugins.connect("notify::active", self.on_use_custom_plugins_toggled)

    def load_defaults(self):
        self.auto_update.set_active(self.settings.settings_json.get("store", {}).get("auto-update", True))
        self.use_custom_stores.set_active(self.settings.settings_json.get("store", {}).get("use-custom-stores", False))
        self.use_custom_plugins.set_active(self.settings.settings_json.get("store", {}).get("use-custom-plugins", False))

    def on_auto_update_toggled(self, *args):
        self.settings.settings_json.setdefault("store", {})
        self.settings.settings_json["store"]["auto-update"] = self.auto_update.get_active()

        # Save
        self.settings.save_json()

    def on_use_custom_stores_toggled(self, *args):
        self.settings.settings_json.setdefault("store", {})
        self.settings.settings_json["store"]["use-custom-stores"] = self.use_custom_stores.get_active()

        self.settings.save_json()

        self.custom_stores.set_sensitive(self.use_custom_stores.get_active())

    def on_use_custom_plugins_toggled(self, *args):
        self.settings.settings_json.setdefault("store", {})
        self.settings.settings_json["store"]["use-custom-plugins"] = self.use_custom_plugins.get_active()

        self.settings.save_json()

        self.custom_plugins.set_sensitive(self.use_custom_plugins.get_active())

class CustomContentGroup(Adw.PreferencesGroup):
    def __init__(self, title: str):
        super().__init__(title=title)

        self.content_adder = CustomContentAdder()
        self.add(self.content_adder)

        self.scroll_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.scroll_box.append(CustomContentEntry(url="https://PAIN", branch="main"))
        self.scroll_box.append(CustomContentEntry(url="https://WORKS", branch="test"))

        self.scroll_view = Gtk.ScrolledWindow()
        self.scroll_view.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        self.scroll_view.set_child(self.scroll_box)

        self.add(self.scroll_view)

class CustomContentAdder(Adw.PreferencesRow):
    def __init__(self):
        super().__init__()

        self.main_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, margin_start=10, valign=Gtk.Align.CENTER)
        self.set_child(self.main_box)

        self.url = Adw.EntryRow(title="Repository URL", valign=Gtk.Align.CENTER)
        self.main_box.append(self.url)

        self.branch = Adw.EntryRow(title="Branch", text="main", valign=Gtk.Align.CENTER)
        self.main_box.append(self.branch)

        self.button_add = Gtk.Button(label="Add", valign=Gtk.Align.CENTER)
        self.main_box.append(self.button_add)

class CustomContentEntry(Adw.PreferencesRow):
    def __init__(self, url: str, branch: str):
        super().__init__()

        self.main_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        self.set_child(self.main_box)

        self.url = Adw.EntryRow(title="Repository URL", valign=Gtk.Align.CENTER, editable=False, text=url, sensitive=False)
        self.main_box.append(self.url)

        self.branch = Adw.EntryRow(title="Branch", valign=Gtk.Align.CENTER, editable=False, text=branch, sensitive=False)
        self.main_box.append(self.branch)

        self.button_remove = Gtk.Button(label="Remove", valign=Gtk.Align.CENTER)
        self.main_box.append(self.button_remove)


class PerformancePage(Adw.PreferencesPage):
    def __init__(self, settings: Settings):
        self.settings = settings
        super().__init__()
        self.set_title(gl.lm.get("settings.performance.title"))
        self.set_icon_name("power-profile-performance-symbolic")

        self.add(PerformancePageGroup(settings=settings))

class PerformancePageGroup(Adw.PreferencesGroup):
    def __init__(self, settings: Settings):
        self.settings = settings
        super().__init__(title=gl.lm.get("settings.performance.header"))

        self.n_cached_pages = Adw.SpinRow.new_with_range(min=0, max=50, step=1)
        self.n_cached_pages.set_title(gl.lm.get("settings.performance.n-cached-pages.title"))
        self.n_cached_pages.set_subtitle(gl.lm.get("settings.performance.n-cached-pages.subtitle"))
        self.n_cached_pages.set_tooltip_text(gl.lm.get("settings.performance.n-cached-pages.tooltip"))
        self.add(self.n_cached_pages)

        self.cache_videos = Adw.SwitchRow(title=gl.lm.get("settings.performance.cache-videos.title"), active=True,
                                          subtitle=gl.lm.get("settings.performance.cache-videos.subtitle"),
                                          tooltip_text=gl.lm.get("settings.performance.cache-videos.tooltip"))
        self.add(self.cache_videos)

        self.load_defaults()

        # Connect signals
        self.n_cached_pages.connect("changed", self.on_n_cached_pages_changed)
        self.cache_videos.connect("notify::active", self.on_cache_videos_toggled)

    def load_defaults(self):
        settings = self.settings.settings_json
        self.n_cached_pages.set_value(settings.get("performance", {}).get("n-cached-pages", 3))
        self.cache_videos.set_active(settings.get("performance", {}).get("cache-videos", True))

    def on_n_cached_pages_changed(self, *args):
        self.settings.settings_json.setdefault("performance", {})
        self.settings.settings_json["performance"]["n-cached-pages"] = int(self.n_cached_pages.get_value())

        # Save
        self.settings.save_json()

        # Update value in page manager
        gl.page_manager.set_n_pages_to_cache(int(self.n_cached_pages.get_value()))

    def on_cache_videos_toggled(self, *args):
        self.settings.settings_json.setdefault("performance", {})
        self.settings.settings_json["performance"]["cache-videos"] = self.cache_videos.get_active()

        # Save
        self.settings.save_json()


class SystemPage(Adw.PreferencesPage):
    def __init__(self, settings: Settings):
        self.settings = settings
        super().__init__()
        self.set_title(gl.lm.get("settings-system-settings-title"))
        self.set_icon_name("system-run-symbolic")

        self.add(SystemGroup(settings=settings))

class SystemGroup(Adw.PreferencesGroup):
    def __init__(self, settings: Settings):
        self.settings = settings
        super().__init__(title=gl.lm.get("settings-system-settings-header"))

        self.autostart = Adw.SwitchRow(title=gl.lm.get("settings-system-settings-autostart"), subtitle=gl.lm.get("settings-system-settings-autostart-subtitle"), active=True)
        self.add(self.autostart)

        self.load_defaults()

        # Connect signals
        self.autostart.connect("notify::active", self.on_autostart_toggled)

    def load_defaults(self):
        self.autostart.set_active(self.settings.settings_json.get("system", {}).get("autostart", True))

    def on_autostart_toggled(self, *args):
        self.settings.settings_json.setdefault("system", {})
        self.settings.settings_json["system"]["autostart"] = self.autostart.get_active()

        setup_autostart(self.autostart.get_active())

        # Save
        self.settings.save_json()