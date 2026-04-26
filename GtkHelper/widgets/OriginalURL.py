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

from src.backend.DeckManagement.HelperMethods import open_web

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk


class OriginalURL(Adw.ActionRow):
    def __init__(self):
        super().__init__(title="Original URL:", subtitle="N/A")
        self.set_activatable(False)

        self.suffix_box = Gtk.Box(valign=Gtk.Align.CENTER)
        self.add_suffix(self.suffix_box)

        self.open_button = Gtk.Button(icon_name="web-browser-symbolic")
        self.open_button.connect("clicked", self.on_open_clicked)
        self.suffix_box.append(self.open_button)

    def set_url(self, url:str):
        if url is None:
            self.set_subtitle("N/A")
            self.open_button.set_sensitive(False)
            return
        self.set_subtitle(url)
        self.open_button.set_sensitive(True)

    def on_open_clicked(self, button:Gtk.Button):
        if self.get_subtitle() in [None, "N/A", ""]:
            return
        open_web(self.get_subtitle())
