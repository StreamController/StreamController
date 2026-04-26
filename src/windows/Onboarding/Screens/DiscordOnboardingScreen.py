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
from typing import TYPE_CHECKING

import gi

from src.backend.DeckManagement.HelperMethods import open_web

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Pango

if TYPE_CHECKING:
    from src.windows.Onboarding.OnboardingWindow import OnboardingWindow


class DiscordOnboardingScreen(Gtk.Box):
    def __init__(self, onboarding_window: "OnboardingWindow"):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, hexpand=True, vexpand=True,
                            halign=Gtk.Align.CENTER, valign=Gtk.Align.CENTER,
                            margin_start=50, margin_end=50, margin_top=50, margin_bottom=50)
        self.onboarding_window = onboarding_window

        self.build()

    def build(self):
        self.label = Gtk.Label(label="Join our Discord", css_classes=["onboarding-welcome-label"],
                                margin_top=20)
        self.append(self.label)

        self.detail = Gtk.Label(label="Join our discord to ask questions, get help and request new features!", css_classes=["onboarding-welcome-detail-label"],
                                width_request=300, halign=Gtk.Align.CENTER, wrap_mode=Pango.WrapMode.WORD_CHAR, wrap=True, justify=Gtk.Justification.CENTER)
        self.append(self.detail)

        self.join_button = Gtk.Button(label="Join", css_classes=["pill", "suggested-action"], margin_top=20, hexpand=False, halign=Gtk.Align.CENTER)
        self.join_button.connect("clicked", self.on_join_button_clicked)
        self.append(self.join_button)

    def on_join_button_clicked(self, button):
        open_web("https://discord.gg/MSyHM8TN3u")
