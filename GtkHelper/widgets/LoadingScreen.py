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
from gi.repository import GLib, Gtk


class LoadingScreen(Gtk.Box):
    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, hexpand=True, vexpand=True,
                         valign=Gtk.Align.CENTER, halign=Gtk.Align.CENTER)

        self.spinner = Gtk.Spinner(spinning=False)
        self.append(self.spinner)

        self.loading_label = Gtk.Label(label="Loading")
        self.append(self.loading_label)

        self.progress_bar = Gtk.ProgressBar(margin_top=20, show_text=True, text="", visible=False)
        self.append(self.progress_bar)

    def set_spinning(self, loading: bool):
        if loading:
            GLib.idle_add(self.spinner.start)
        else:
            GLib.idle_add(self.spinner.stop)
