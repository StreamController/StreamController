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
import asyncio
import threading
from typing import TYPE_CHECKING

import gi

import globals as gl

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import GLib, Gtk

if TYPE_CHECKING:
    from src.windows.Onboarding.OnboardingWindow import OnboardingWindow


class OnboardingScreen5(Gtk.Box):
    def __init__(self, onboarding_window: "OnboardingWindow"):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, hexpand=True, vexpand=True,
                         halign=Gtk.Align.CENTER, valign=Gtk.Align.CENTER)
        self.onboarding_window = onboarding_window

        self.build()

    def build(self):
        self.label = Gtk.Label(label=gl.lm.get("onboarding.ready.header"), css_classes=["onboarding-welcome-label"],
                               margin_top=0)
        self.append(self.label)

        self.start_button = Gtk.Button(label=gl.lm.get("onboarding.ready.button"), css_classes=["pill", "suggested-action"], margin_top=20)
        self.start_button.connect("clicked", self.on_start_button_click)
        self.append(self.start_button)

    def on_start_button_click(self, button):
        threading.Thread(target=self._on_start_button_click).start()

    def _on_start_button_click(self):
        GLib.idle_add(self.onboarding_window.stack.set_visible_child_name, "loading")
        GLib.idle_add(self.onboarding_window.loading_box.loading_label.set_label, "Installing plugins")
        GLib.idle_add(self.onboarding_window.loading_box.set_spinning, True)

        plugins = self.onboarding_window.recommendations.get_selected_plugins()

        GLib.idle_add(self.onboarding_window.loading_box.progress_bar.set_visible, len(plugins) > 0)

        for i, plugin_data in enumerate(plugins):
            GLib.idle_add(self.onboarding_window.loading_box.progress_bar.set_text, f"Installing {plugin_data.plugin_name}")
            GLib.idle_add(self.onboarding_window.loading_box.progress_bar.set_fraction, i / len(plugins))
            plugin = asyncio.run(gl.store_backend.get_plugin_for_id(plugin_data.plugin_id))
            if plugin is None:
                continue
            asyncio.run(gl.store_backend.install_plugin(plugin))

        GLib.idle_add(self.onboarding_window.loading_box.set_spinning, False)
        GLib.idle_add(self.onboarding_window.close)
        GLib.idle_add(self.onboarding_window.on_close)
        GLib.idle_add(gl.app.main_win.show)
