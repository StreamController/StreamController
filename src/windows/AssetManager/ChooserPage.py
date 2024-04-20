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
from gi.repository import Gtk, Gdk, GLib

import globals as gl

class ChooserPage(Gtk.Stack):
    def __init__(self):
        super().__init__(margin_start=15, margin_end=15, margin_top=15, margin_bottom=15)
        self._build()

        self.init_dnd()

    def _build(self):
        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, hexpand=True, vexpand=True)
        self.add_titled(self.main_box, "main", "main")

        self.nav_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, hexpand=True, vexpand=False, margin_bottom=15)
        self.main_box.append(self.nav_box)

        self.search_entry = Gtk.SearchEntry(placeholder_text="Search", hexpand=True)
        self.search_entry.connect("search-changed", self.on_search_changed)
        self.nav_box.append(self.search_entry)

        self.type_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, css_classes=["linked"], margin_start=15)
        self.nav_box.append(self.type_box)

        self.video_button = Gtk.ToggleButton(icon_name="camera-video-symbolic", css_classes=["blue-toggle-button"])
        self.video_button.connect("toggled", self.on_video_toggled)
        self.type_box.append(self.video_button)

        self.image_button = Gtk.ToggleButton(icon_name="camera-photo-symbolic", css_classes=["blue-toggle-button"])
        self.image_button.connect("toggled", self.on_image_toggled)
        self.type_box.append(self.image_button)

        self.scrolled_window = Gtk.ScrolledWindow(hexpand=True, vexpand=True)
        self.main_box.append(self.scrolled_window)

        self.scrolled_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, hexpand=True, vexpand=False,
                                margin_top=5, margin_bottom=5)
        self.scrolled_window.set_child(self.scrolled_box)

        self.inside_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, hexpand=True, vexpand=False)
        self.scrolled_box.append(self.inside_box)


        # Add vexpand box to the bottom to avoid unwanted stretching of the children
        self.fix_box = Gtk.Box(vexpand=True, hexpand=True)
        self.scrolled_box.append(self.fix_box)


        ## Loading box
        self.loading_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, hexpand=True, vexpand=True,
                                   valign=Gtk.Align.CENTER, halign=Gtk.Align.CENTER)
        self.add_titled(self.loading_box, "loading", "loading")

        self.spinner = Gtk.Spinner(spinning=False)
        self.loading_box.append(self.spinner)

        self.loading_label = Gtk.Label(label=gl.lm.get("store.page.loading-spinner.label"))
        self.loading_box.append(self.loading_label)

        self.set_loading(True)

    def set_loading(self, loading: bool) -> None:
        if loading:
            GLib.idle_add(self.set_visible_child_name, "loading")
            GLib.idle_add(self.spinner.start)
        else:
            GLib.idle_add(self.set_visible_child_name, "main")
            GLib.idle_add(self.spinner.stop)

    def init_dnd(self):
        self.dnd_target = Gtk.DropTarget.new(Gdk.FileList, Gdk.DragAction.COPY)
        self.dnd_target.connect("drop", self.on_dnd_drop)
        self.dnd_target.connect("accept", self.on_dnd_accept)

        self.main_box.add_controller(self.dnd_target)

    def on_dnd_accept(self, drop, user_data):
        pass
    
    def on_dnd_drop(self, drop_target, value, x, y):
        pass

    def show_for_path(self, path, callback_func=None, *callback_args, **callback_kwargs):
        pass

    def on_video_toggled(self, button):
        pass

    def on_image_toggled(self, button):
        pass

    def on_search_changed(self, entry):
        pass