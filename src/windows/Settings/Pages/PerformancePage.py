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

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw

if TYPE_CHECKING:
    from src.windows.Settings.Settings import Settings


class PerformancePage(Adw.PreferencesPage):
    def __init__(self, settings: "Settings"):
        self.settings = settings
        super().__init__()
        self.set_title(gl.lm.get("settings.performance.title"))
        self.set_icon_name("power-profile-performance-symbolic")

        self.add(PerformancePageGroup(settings=settings))

class PerformancePageGroup(Adw.PreferencesGroup):
    def __init__(self, settings: "Settings"):
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
        gl.page_manager.set_pages_to_cache(int(self.n_cached_pages.get_value()))

    def on_cache_videos_toggled(self, *args):
        self.settings.settings_json.setdefault("performance", {})
        self.settings.settings_json["performance"]["cache-videos"] = self.cache_videos.get_active()

        # Save
        self.settings.save_json()
