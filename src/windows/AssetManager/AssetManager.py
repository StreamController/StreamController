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
# Import gtk modules
import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, GLib, Gio, Pango, GdkPixbuf, GObject

# Import Python modules
from loguru import logger as log
import os
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from src.windows.mainWindow.mainWindow import MainWindow

# Import globals
import globals as gl

class AssetManager(Gtk.ApplicationWindow):
    def __init__(self, main_window: "MainWindow", *args, **kwargs):
        super().__init__(
            title="Asset Manager",
            default_width=1050,
            default_height=750,
            transient_for=main_window,
            *args, **kwargs
            )
        self.main_window = main_window
        self.build()

    def build(self):
        self.scrolled_window = Gtk.ScrolledWindow(hexpand=True, vexpand=False)
        self.set_child(self.scrolled_window)

        self.main_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, hexpand=False, vexpand=False,
                                margin_start=5, margin_end=5, margin_top=5, margin_bottom=5)
        self.scrolled_window.set_child(self.main_box)

        self.asset_chooser = AssetChooser(self)
        self.main_box.append(self.asset_chooser)


class AssetChooser(Gtk.GridView):
    def __init__(self, *args, **kwargs):
        super().__init__()
        self.build()

    def build(self):
        list_store = Gio.ListStore()
        for asset in gl.asset_manager.get_all():
            list_store.append(Asset(asset["name"], asset["internal-path"]))

        single_selection = Gtk.SingleSelection()
        single_selection.set_model(list_store)

        self.set_model(single_selection)

        factory = Gtk.SignalListItemFactory()
        def factory_setup(fact, item):
            item.box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, width_request=250)
            item.set_child(item.box)

            item.picture = Gtk.Picture(vexpand=True, width_request=250, height_request=180, overflow=Gtk.Overflow.HIDDEN, content_fit=Gtk.ContentFit.COVER)
            item.box.append(item.picture)

            item.label = Gtk.Label()
            item.box.append(item.label)


        factory.connect("setup", factory_setup)

        def factory_bind(fact, item):
            item.label.set_text(item.get_item().name)
            item.picture.set_file(Gio.File.new_for_path(item.get_item().image_path))

        factory.connect("bind", factory_bind)

        self.set_factory(factory)


class Asset(GObject.Object):
    name = GObject.Property(type=str)
    image_path = GObject.Property(type=str)
    def __init__(self, name, image_path):
        super().__init__()
        self.name = name
        self.image_path = image_path