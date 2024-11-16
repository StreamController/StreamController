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
import globals as gl

from gi.repository import Gtk, Adw

from src.windows.Onboarding.OnboardingWindow import SupportAppOnboardingScreen

class DonateWindow(Adw.Dialog):
    def __init__(self):
        super().__init__(title="Support the project", accessible_role=Gtk.AccessibleRole.DIALOG)
        self.set_presentation_mode(Adw.DialogPresentationMode.FLOATING)
        self.set_can_close(True)
        self.set_content_height(600)
        self.set_content_width(600)
        self.set_follows_content_size(False)

        self.build()

    def build(self):
        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, hexpand=True)
        self.set_child(self.main_box)

        self.support_screen = SupportAppOnboardingScreen()
        self.main_box.append(self.support_screen)

        self.button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, margin_start=15, margin_end=15, margin_top=15, margin_bottom=15)
        self.main_box.append(self.button_box)

        self.dont_show_again_button = Gtk.Button(label="Close & Don't show again")
        self.dont_show_again_button.connect("clicked", self.on_click_dont_show_again)
        self.button_box.append(self.dont_show_again_button)

        self.button_box.append(Gtk.Box(hexpand=True))

        self.button = Gtk.Button(label="Close", css_classes=["suggested-action"])
        self.button.connect("clicked", self.on_click_close)
        self.button_box.append(self.button)

    def on_click_dont_show_again(self, widget):
        self.close()

        app_settings = gl.settings_manager.get_app_settings()
        app_settings.setdefault("general", {})
        app_settings["general"]["show-donate-window"] = False
        gl.settings_manager.save_app_settings(app_settings)

    def on_click_close(self, widget):
        self.close()