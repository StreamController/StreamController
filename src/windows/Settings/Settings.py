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

from GtkHelper.GtkHelper import BetterPreferencesGroup
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
        self.set_default_size(1000, 700)

        # Center settings win over main_win (depends on DE)
        self.set_transient_for(gl.app.main_win)
        # Allow interaction with other windows
        self.set_modal(False)

        self.settings_json:dict = None
        self.load_json()

        self.general_page = GeneralPage(settings=self)
        self.ui_page = UIPage(settings=self)
        self.store_page = StorePage(settings=self)
        self.performance_page = PerformancePage(settings=self)
        self.dev_page = DevPage(settings=self)
        self.system_page = SystemPage(settings=self)

        self.add(self.general_page)
        self.add(self.ui_page)
        self.add(self.store_page)
        self.add(self.performance_page)
        self.add(self.system_page)
        self.add(self.dev_page)

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

        self.auto_config_row = Adw.SwitchRow(title=gl.lm.get("settings-auto-open-action-config"), subtitle=gl.lm.get("settings-auto-open-action-config-subtitle"), active=True)
        self.add(self.auto_config_row)

        self.load_defaults()

        # Connect signals
        self.emulate_row.connect("notify::active", self.on_emulate_row_toggled)
        self.enable_fps_warnings_row.connect("notify::active", self.on_enable_fps_warnings_row_toggled)
        self.allow_white_mode.connect("notify::active", self.on_allow_white_mode_toggled)
        self.show_notifications.connect("notify::active", self.on_show_notifications_toggled)
        self.auto_config_row.connect("notify::active", self.on_auto_config_row_toggled)

    def load_defaults(self):
        self.emulate_row.set_active(self.settings.settings_json.get("key-grid", {}).get("emulate-at-double-click", True))
        self.enable_fps_warnings_row.set_active(self.settings.settings_json.get("warnings", {}).get("enable-fps-warnings", True))
        self.allow_white_mode.set_active(self.settings.settings_json.get("ui", {}).get("allow-white-mode", False))
        self.show_notifications.set_active(self.settings.settings_json.get("ui", {}).get("show-notifications", True))
        self.auto_config_row.set_active(self.settings.settings_json.get("ui", {}).get("auto-open-action-config", True))

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

    def on_auto_config_row_toggled(self, *args):
        self.settings.settings_json.setdefault("ui", {})
        self.settings.settings_json["ui"]["auto-open-action-config"] = self.auto_config_row.get_active()

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


class GeneralPage(Adw.PreferencesPage):
    def __init__(self, settings: Settings):
        self.settings = settings
        super().__init__()
        self.set_title("General")
        self.set_icon_name("open-menu-symbolic")

        self.add(GeneralPageGroup(settings=settings))

class GeneralPageGroup(Adw.PreferencesGroup):
    def __init__(self, settings: Settings):
        self.settings = settings
        super().__init__(title=gl.lm.get("General app settings"))

        self.hold_time_row = Adw.SpinRow.new_with_range(min=0.1, max=3, step=0.1)
        self.hold_time_row.set_title("Minimum hold duration (s)")
        self.hold_time_row.set_subtitle("Minimum hold duration for keys and dials")
        self.hold_time_row.set_range(0.1, 3)
        self.add(self.hold_time_row)

        self.load_defaults()

        # Connect signals
        self.hold_time_row.connect("changed", self.on_n_fake_decks_row_changed)

    def load_defaults(self):
        self.hold_time_row.set_value(self.settings.settings_json.get("general", {}).get("hold-time", 0.5))

    def on_n_fake_decks_row_changed(self, *args):
        self.settings.settings_json.setdefault("general", {})
        self.settings.settings_json["general"]["hold-time"] = self.hold_time_row.get_value()

        for controller in gl.deck_manager.deck_controller:
            controller.hold_time = self.hold_time_row.get_value()

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

        self.keep_running = Adw.SwitchRow(title=gl.lm.get("settings-system-settings-keep-running"), subtitle=gl.lm.get("settings-system-settings-keep-running-subtitle"), active=False)
        self.add(self.keep_running)

        self.autostart = Adw.SwitchRow(title=gl.lm.get("settings-system-settings-autostart"), subtitle=gl.lm.get("settings-system-settings-autostart-subtitle"), active=True)
        self.add(self.autostart)

        self.lock_on_lock_screen = Adw.SwitchRow(title="Lock decks when screen is locked", subtitle="Only works on Gnome", active=True)
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
        self.beta_resume_mode.set_active(self.settings.settings_json.get("system", {}).get("beta-resume-mode", False))

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