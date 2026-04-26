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
import os
import subprocess
from typing import TYPE_CHECKING

import gi
from packaging import version

import globals as gl
from autostart import is_flatpak
from GtkHelper.GtkHelper import LoadingScreen
from src.windows.Onboarding.PluginRecommendations import PluginRecommendations
from src.windows.Onboarding.Screens.DiscordOnboardingScreen import DiscordOnboardingScreen
from src.windows.Onboarding.Screens.ExtensionOnboardingScreen import ExtensionOnboardingScreen
from src.windows.Onboarding.Screens.IconOnboardingScreen import IconOnboardingScreen
from src.windows.Onboarding.Screens.ImageOnboardingScreen import ImageOnboardingScreen
from src.windows.Onboarding.Screens.OnboardingScreen5 import OnboardingScreen5
from src.windows.Onboarding.Screens.SupportAppOnboardingScreen import (
    SupportAppOnboardingScreen,
)
from src.windows.Onboarding.Screens.UdevOnboardingScreen import UdevOnboardingScreen

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk

if TYPE_CHECKING:
    from windows.mainWindow.mainWindow import MainWindow

__all__ = [
    "DiscordOnboardingScreen",
    "ExtensionOnboardingScreen",
    "IconOnboardingScreen",
    "ImageOnboardingScreen",
    "OnboardingScreen5",
    "OnboardingWindow",
    "SupportAppOnboardingScreen",
    "UdevOnboardingScreen",
]


class OnboardingWindow(Adw.Dialog):
    def __init__(self, application, main_win: "MainWindow"):
        super().__init__()
        self.set_title("Onboarding")
        self.set_presentation_mode(Adw.DialogPresentationMode.FLOATING)
        self.set_can_close(True)
        self.set_content_height(600)
        self.set_content_width(600)
        self.set_follows_content_size(False)

        self.connect("close-attempt", self.on_close)
        
        self.build()

    def build(self):
        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, hexpand=True, vexpand=True)
        self.set_child(self.main_box)

        self.header = Adw.HeaderBar(css_classes=["flat"])
        self.main_box.append(self.header)

        self.stack = Gtk.Stack(hexpand=True, vexpand=True)
        self.main_box.append(self.stack)

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
        self.carousel.append(IconOnboardingScreen("go-home-symbolic", gl.lm.get("onboarding.store.header"), gl.lm.get("onboarding.store.details")))
        self.carousel.append(IconOnboardingScreen("view-paged-symbolic", gl.lm.get("onboarding.multiple.header"), gl.lm.get("onboarding.multiple.details")))
        self.carousel.append(IconOnboardingScreen("preferences-desktop-remote-desktop-symbolic", gl.lm.get("onboarding.productive.header"), gl.lm.get("onboarding.productive.details")))
        #TODO: Add discord screen
        desktop = os.getenv("XDG_CURRENT_DESKTOP")
        if desktop is not None:
            if desktop.lower() == "gnome":
                self.carousel.append(ExtensionOnboardingScreen())

        udev_version = self.get_udev_version()
        if udev_version is not None:
            if version.parse(udev_version) < version.parse("252"):
                self.carousel.append(UdevOnboardingScreen())

        self.recommendations = PluginRecommendations()
        self.carousel.append(self.recommendations)

        self.discord_page = DiscordOnboardingScreen(self)
        self.carousel.append(self.discord_page)

        self.support_app_page = SupportAppOnboardingScreen()
        self.carousel.append(self.support_app_page)

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
        if hasattr(gl.app, "permissions"):
            gl.app.permissions.present()

    def get_udev_version(self):
        command = "udevadm --version"

        if is_flatpak():
            command = f"flatpak run --command {command}"

        try:
            return subprocess.check_output(command, shell=True).decode("utf-8").strip()
        except subprocess.CalledProcessError:
            return None
