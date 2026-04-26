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

from src.backend.DeckManagement.HelperMethods import run_command

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Pango


class SupportAppOnboardingScreen(Gtk.Box):
    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, hexpand=True, vexpand=True,
                         halign=Gtk.Align.CENTER, valign=Gtk.Align.CENTER,
                         margin_start=50, margin_end=50, margin_top=50, margin_bottom=50)

        self.build()

    def build(self):
        self.label = Gtk.Label(label="Support the app\ndevelopment", css_classes=["onboarding-welcome-label"],
                               margin_bottom=70, use_markup=True, justify=Gtk.Justification.CENTER)
        self.append(self.label)

        self.detail = Gtk.Label(label="Creating this app was a lot of work, and your support helps me continue to further improve it. Consider donating to enable me to dedicate more time to new features and enhancements.", css_classes=["onboarding-welcome-detail-label"],
                                width_request=300, halign=Gtk.Align.CENTER, wrap_mode=Pango.WrapMode.WORD_CHAR, wrap=True, justify=Gtk.Justification.CENTER, use_markup=True)
        self.append(self.detail)

        self.support_button = Gtk.Button(label="Donate", css_classes=["pill", "suggested-action"], margin_top=90, hexpand=False, halign=Gtk.Align.CENTER)
        self.support_button.connect("clicked", self.on_support_button_clicked)
        self.append(self.support_button)

    def on_support_button_clicked(self, button):
        run_command("xdg-open https://ko-fi.com/core447")
        # portal = Xdp.Portal.new()
        # portal.open_uri(
        #     parent=XdpGtk4.parent_new_gtk(gl.app.get_active_window()),
        #     uri="https://ko-fi.com/core447",
        #     flags=Xdp.OpenUriFlags.ASK,
        #     cancellable=None,
        #     callback=self.callback
        # )

    def callback(self, source, res):
        print(source)
        print(res)
