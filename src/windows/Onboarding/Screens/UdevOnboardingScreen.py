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

import globals as gl
from src.backend.DeckManagement.HelperMethods import open_web

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Pango


class UdevOnboardingScreen(Gtk.Box):
    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, hexpand=True)

        self.build()

    def build(self):
        self.image = Gtk.Image(icon_name="dialog-error-symbolic", pixel_size=250, margin_top=70)
        self.append(self.image)

        self.label = Gtk.Label(label=gl.lm.get("onboarding.udev.header"), css_classes=["onboarding-welcome-label"], margin_top=50)
        self.append(self.label)

        self.detail = Gtk.Label(label=gl.lm.get("onboarding.udev.detail"), css_classes=["onboarding-welcome-detail-label"],
                                width_request=600, halign=Gtk.Align.CENTER, wrap_mode=Pango.WrapMode.WORD_CHAR, wrap=True, justify=Gtk.Justification.CENTER)
        self.append(self.detail)

        self.open_wiki_button = Gtk.Button(label=gl.lm.get("onboarding.udev.button"), margin_top=20, halign=Gtk.Align.CENTER, css_classes=["pill", "suggested-action"])
        self.open_wiki_button.connect("clicked", self.on_button_click)
        self.append(self.open_wiki_button)

    def on_button_click(self, button):
        open_web("https://streamcontroller.github.io/docs/latest/installation/#udev")
