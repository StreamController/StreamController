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

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import GLib, Gtk, Pango


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
                                width_request=600, halign=Gtk.Align.CENTER, wrap_mode=Pango.WrapMode.WORD_CHAR, wrap=True, justify=Gtk.Justification.CENTER)
        self.append(self.detail)

        self.install_button = Gtk.Button(label=gl.lm.get("onboarding.extension.install-button"), margin_top=20, halign=Gtk.Align.CENTER)
        self.update_button_status()
        self.install_button.connect("clicked", self.on_install_button_click)
        self.append(self.install_button)

        self.hint_label = Gtk.Label(label=gl.lm.get("onboarding.extension.hint"), sensitive=False, margin_top=20, use_markup=True)
        self.append(self.hint_label)

    def update_button_status(self) -> None:
        installed_extensions = gl.gnome_extensions.get_installed_extensions()
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
