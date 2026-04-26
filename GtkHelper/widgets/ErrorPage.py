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
import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk


class ErrorPage(Gtk.Box):
    def __init__(self, reload_func: callable = None,
                 error_text:str = "Error",
                 reload_args = []):
        super().__init__(orientation=Gtk.Orientation.VERTICAL,
                         halign=Gtk.Align.CENTER,
                         valign=Gtk.Align.CENTER)

        self.reload_func = reload_func
        self.error_text = error_text
        self.reload_args = reload_args
        self.build()

    def build(self):
        self.error_label = Gtk.Label(label=self.error_text)
        self.append(self.error_label)

        self.retry_button = Gtk.Button(label="Retry")
        self.retry_button.connect("clicked", self.on_retry_button_click)

        if callable(self.reload_func):
            self.append(self.retry_button)

    def on_retry_button_click(self, button):
        self.reload_func(*self.reload_args)

    def set_error_text(self, error_text):
        self.error_label.set_text(error_text)

    def set_reload_func(self, reload_func):
        if callable(self.reload_func):
            if callable(reload_func):
                self.reload_func = reload_func
            else:
                self.remove(self.retry_button)
        else:
            self.append(self.retry_button)
            self.reload_func = reload_func

    def set_reload_args(self, reload_args):
        self.reload_args = reload_args
