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

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk


class ImageOnboardingScreen(Gtk.Box):
    def __init__(self, image_path: str, label: str, detail: str):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, hexpand=True)
        self.image_path = image_path
        self.label = label
        self.detail = detail

        self.build()

    def build(self):
        self.image = Gtk.Image(file=self.image_path, css_classes=["onboarding-image"], margin_top=70)
        self.append(self.image)

        self.label = Gtk.Label(label=self.label, css_classes=["onboarding-welcome-label"],
                               margin_top=20)
        self.append(self.label)

        self.detail = Gtk.Label(label=self.detail, css_classes=["onboarding-welcome-detail-label"],
                                margin_top=8)
        self.append(self.detail)
