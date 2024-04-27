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
# Import gtk modules
from asyncio import wrap_future
import asyncio
import os
import threading
import gi
import subprocess
from packaging import version
import webbrowser as web

from GtkHelper.GtkHelper import LoadingScreen
from autostart import is_flatpak
from src.windows.Onboarding.PluginRecommendations import PluginRecommendations

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, Pango, GLib

# Import globals
import globals as gl

# Import typing
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from windows.mainWindow.mainWindow import MainWindow


class OnboardingWindow(Gtk.ApplicationWindow):
    def __init__(self, application, main_win: "MainWindow"):
        super().__init__(application=application)
        self.set_title("Onboarding")
        self.set_transient_for(main_win)
        self.set_modal(True)
        self.set_default_size(700, 700)

        self.connect("close-request", self.on_close)
        
        self.build()

    def build(self):
        self.header = Adw.HeaderBar(css_classes=["flat"])
        self.set_titlebar(self.header)

        self.stack = Gtk.Stack(hexpand=True, vexpand=True)
        self.set_child(self.stack)

        self.overlay = Gtk.Overlay()
        self.stack.add_named(self.overlay, "main")

        self.carousel = Adw.Carousel(
            allow_long_swipes=True,
            allow_scroll_wheel=True,
            allow_mouse_drag=True,
            reveal_duration=200,
        )
        self.carousel.connect("page-changed", self.on_page_changed)
        self.overlay.set_child(self.carousel)

        self.carousel.append(ImageOnboardingScreen("Assets/Onboarding/icon.png", gl.lm.get("onboarding.welcome.header"), gl.lm.get("onboarding.welcome.details")))
        self.carousel.append(IconOnboardingScreen("go-home", gl.lm.get("onboarding.store.header"), gl.lm.get("onboarding.store.details")))
        self.carousel.append(IconOnboardingScreen("view-paged", gl.lm.get("onboarding.multiple.header"), gl.lm.get("onboarding.multiple.details")))
        self.carousel.append(IconOnboardingScreen("preferences-desktop-remote-desktop-symbolic", gl.lm.get("onboarding.productive.header"), gl.lm.get("onboarding.productive.details")))
        if os.getenv("XDG_CURRENT_DESKTOP").lower() == "gnome":
            self.carousel.append(ExtensionOnboardingScreen())
        self.recommendations = PluginRecommendations()
        self.carousel.append(self.recommendations)

        self.carousel.append(OnboardingScreen5(self))

        self.carousel_indicator_dots = Adw.CarouselIndicatorDots(carousel=self.carousel)
        self.header.set_title_widget(self.carousel_indicator_dots)

        self.forward_button = Gtk.Button(icon_name="go-next-symbolic", css_classes=["onboarding-nav-button", "circular", "suggested-action"],
                                         halign=Gtk.Align.END, valign=Gtk.Align.CENTER, margin_end=15)
        self.forward_button.connect("clicked", self.on_forward_button_click)
        self.overlay.add_overlay(self.forward_button)

        self.back_button = Gtk.Button(icon_name="go-previous-symbolic", css_classes=["onboarding-nav-button", "circular", "suggested-action"],
                                      halign=Gtk.Align.START, valign=Gtk.Align.CENTER, margin_start=15,
                                      visible=False)
        self.back_button.connect("clicked", self.on_back_button_click)
        self.overlay.add_overlay(self.back_button)

        # Add loading screen
        self.loading_box = LoadingScreen()
        self.stack.add_named(self.loading_box, "loading")

    def on_forward_button_click(self, button):
        pos = self.carousel.get_position()
        pos += 1

        # Theoretically not necessary because on_page_changed handles it but it takes some time and therefore doesn't feel nice
        if pos >= self.carousel.get_n_pages() -1:
            self.forward_button.set_visible(False)
        self.back_button.set_visible(True)

        scroll_to_widget = self.carousel.get_nth_page(pos)
        self.carousel.scroll_to(scroll_to_widget, True)

    def on_back_button_click(self, button):
        pos = self.carousel.get_position()
        pos -= 1

        # Theoretically not necessary because on_page_changed handles it but it takes some time and therefore doesn't feel nice
        if pos <= 0:
            self.back_button.set_visible(False)
        self.forward_button.set_visible(True)

        scroll_to_widget = self.carousel.get_nth_page(pos)
        self.carousel.scroll_to(scroll_to_widget, True)

    def on_page_changed(self, carousel: Adw.Carousel, page_index: int) -> None:
        if page_index > 0:
            self.back_button.set_visible(True)
        else:
            self.back_button.set_visible(False)

        if page_index < carousel.get_n_pages() - 1:
            self.forward_button.set_visible(True)
        else:
            self.forward_button.set_visible(False)

    def on_close(self, *args, **kwargs):
        self.destroy()
        if hasattr(gl.app, "permissions"):
            gl.app.permissions.present()

class ImageOnboardingScreen(Gtk.Box):
    def __init__(self, image_path: str, label: str, detail: str):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, hexpand=True)
        self.image_path = image_path
        self.label = label
        self.detail = detail

        self.build()

    def build(self):
        self.image = Gtk.Image(file=self.image_path, css_classes=["onboarding-image"], margin_top=120)
        self.append(self.image)

        self.label = Gtk.Label(label=self.label, css_classes=["onboarding-welcome-label"],
                               margin_top=50)
        self.append(self.label)

        self.detail = Gtk.Label(label=self.detail, css_classes=["onboarding-welcome-detail-label"],)
        self.append(self.detail)

class IconOnboardingScreen(Gtk.Box):
    def __init__(self, icon_name: str, label: str, detail: str):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, hexpand=True)
        self.icon_name = icon_name
        self.label = label
        self.detail = detail

        self.build()

    def build(self):
        self.image = Gtk.Image(icon_name=self.icon_name, pixel_size=350, margin_top=120)
        self.append(self.image)

        self.label = Gtk.Label(label=self.label, css_classes=["onboarding-welcome-label"],
                               margin_top=50)
        self.append(self.label)

        self.detail = Gtk.Label(label=self.detail, css_classes=["onboarding-welcome-detail-label"],)
        self.append(self.detail)


class ExtensionOnboardingScreen(Gtk.Box):
    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, hexpand=True)

        self.build()

    def build(self):
        self.image = Gtk.Image(icon_name="folder-download-symbolic", pixel_size=250, margin_top=70)
        self.append(self.image)

        self.label = Gtk.Label(label=gl.lm.get("onboarding.extension.header"), css_classes=["onboarding-welcome-label"], margin_top=50)
        self.append(self.label)

        self.detail = Gtk.Label(label=gl.lm.get("onboarding.extension.detail"), css_classes=["onboarding-welcome-detail-label"],
                                width_request=600, halign=Gtk.Align.CENTER, wrap_mode=Gtk.WrapMode.WORD_CHAR, wrap=True, justify=Gtk.Justification.CENTER)
        self.append(self.detail)

        self.install_button = Gtk.Button(label=gl.lm.get("onboarding.extension.install-button"), margin_top=20, halign=Gtk.Align.CENTER)
        self.update_button_status()
        self.install_button.connect("clicked", self.on_install_button_click)
        self.append(self.install_button)

        self.hint_label = Gtk.Label(label=gl.lm.get("onboarding.extension.hint"), sensitive=False, margin_top=20)
        self.append(self.hint_label)

    def update_button_status(self) -> None:
        installed_extensions = gl.gnome_extensions.get_installed_extensions()
        print(installed_extensions)
        installed = "streamcontroller@core447.com" in installed_extensions
        if installed:
            self.set_button_status("installed")
        else:
            self.set_button_status("uninstalled")

    def set_button_status(self, status: str) -> None:
        """
        uninstalled, installed, failed
        """
        self.install_button.set_css_classes(["pill"])
        if status == "uninstalled":
            self.install_button.add_css_class("suggested-action")
            self.install_button.set_label(gl.lm.get("onboarding.extension.button.install"))
            self.install_button.set_sensitive(True)
        elif status == "installed":
            self.install_button.add_css_class("success")
            self.install_button.set_label(gl.lm.get("onboarding.extension.button.installed"))
            self.install_button.set_sensitive(False)
        elif status == "failed":
            self.install_button.add_css_class("destructive-action")
            self.install_button.set_label(gl.lm.get("onboarding.extension.button.failed"))
            self.install_button.set_sensitive(False)
            # Allow retry after 1 second
            GLib.timeout_add(1000, self.set_button_status, "uninstalled")
            
        # To stop potential GLib.timeout_add
        return False


    def on_install_button_click(self, button):
        result = gl.gnome_extensions.request_installation("streamcontroller@core447.com")
        if result:
            self.set_button_status("installed")
        else:
            self.set_button_status("failed")
        gl.window_grabber.init_integration()

class OnboardingScreen5(Gtk.Box):
    def __init__(self, onboarding_window: OnboardingWindow):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, hexpand=True, vexpand=True,
                         halign=Gtk.Align.CENTER, valign=Gtk.Align.CENTER)
        self.onboarding_window = onboarding_window

        self.build()

    def build(self):
        self.label = Gtk.Label(label=gl.lm.get("onboarding.ready.header"), css_classes=["onboarding-welcome-label"],
                               margin_top=50)
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

        selected_ids = self.onboarding_window.recommendations.get_selected_ids()

        for plugin_id in selected_ids:
            plugin = asyncio.run(gl.store_backend.get_plugin_for_id(plugin_id))
            if plugin is None:
                continue
            asyncio.run(gl.store_backend.install_plugin(plugin))

        GLib.idle_add(self.onboarding_window.loading_box.set_spinning, False)
        GLib.idle_add(self.onboarding_window.close)
        GLib.idle_add(self.onboarding_window.destroy)
        GLib.idle_add(self.onboarding_window.on_close)
        GLib.idle_add(gl.app.main_win.show)