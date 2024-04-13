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
# Import gi
import os
import gi

from src.windows.PageManager.Importer.StreamDeckUI.StreamDeckUI import StreamDeckUIImporter

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, Gio, GLib

class Importer(Adw.ApplicationWindow):
    def __init__(self, app, window):
        super().__init__(application=app,
                         transient_for=window,
                         modal=True,
                         default_width=400,
                         default_height=120,
                         title="Importing")

        self.build()

    def build(self):
        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.set_content(self.main_box)

        self.header = Adw.HeaderBar(css_classes=["flat"])
        self.main_box.append(self.header)

        self.progess_bar = Gtk.ProgressBar(margin_start=20, margin_end=20, margin_top=20, margin_bottom=20, show_text=True)
        self.main_box.append(self.progess_bar)

    def show_error(self):
        pass

    def import_pages(self, path: str, app: str) -> None:
        self.progess_bar.set_text("Importing...")
        self.progess_bar.set_fraction(0)

        if app == "streamdeck-ui":
            self.import_from_streamdeck_ui(path)

        self.progess_bar.set_text("Imported!")
        self.progess_bar.set_fraction(1)

        GLib.timeout_add(2000, self.close)

    def import_from_streamdeck_ui(self, path: str) -> None:
        if not os.path.exists(path):
            self.show_error()
            return
        if not os.path.splitext(os.path.basename(path))[1] == ".json":
            self.show_error()
            return

        ui_importer = StreamDeckUIImporter(path)
        ui_importer.start_import()