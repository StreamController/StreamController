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
from io import BytesIO

import gi
import globals as gl

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, GdkPixbuf, Pango, Gio

MDI_SIZE = 200

class Preview(Gtk.FlowBoxChild):
    def __init__(self, image_path: str = None, text:str = None, can_be_deleted: bool = False, has_info: bool = True):
        super().__init__()
        self.set_css_classes(["asset-preview"])
        self.set_margin_start(5)
        self.set_margin_end(5)
        self.set_margin_top(5)
        self.set_margin_bottom(5)

        self.pixbuf: GdkPixbuf.Pixbuf = None
        self.can_be_deleted = can_be_deleted
        self.has_info = has_info

        self._build()

        if image_path is not None:
            self.set_image(image_path)
        if text is not None:
            self.set_text(text)

    def _build(self):
        self.overlay = Gtk.Overlay()
        self.set_child(self.overlay)

        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, width_request=250, height_request=180)
        self.overlay.set_child(self.main_box)

        self.picture = Gtk.Picture(overflow=Gtk.Overflow.HIDDEN, content_fit=Gtk.ContentFit.COVER,
                                   hexpand=False, vexpand=False, keep_aspect_ratio=True)

        self.picture.set_pixbuf(self.pixbuf)
        self.main_box.append(self.picture)

        self.label = Gtk.Label(xalign=Gtk.Align.CENTER, hexpand=False, ellipsize=Pango.EllipsizeMode.END, max_width_chars=20,
                               margin_start=20, margin_end=20)
        self.main_box.append(self.label)

        self.info_button = Gtk.Button(icon_name="help-about-symbolic", halign=Gtk.Align.START, valign=Gtk.Align.END, margin_start=5, margin_bottom=5, visible=self.has_info)
        self.info_button.connect("clicked", self.on_click_info)
        self.overlay.add_overlay(self.info_button)

        self.remove_button = Gtk.Button(icon_name="user-trash-symbolic", valign=Gtk.Align.END, halign=Gtk.Align.END, margin_end=5, margin_bottom=5, visible=self.can_be_deleted)
        self.remove_button.connect("clicked", self.on_click_remove)
        self.overlay.add_overlay(self.remove_button)

    def set_image(self, path:str):
        path = str(path)

        if path is None:
            self.pixbuf = GdkPixbuf.Pixbuf.new(width=250, height=180)
            return

        if path.startswith("<svg "):
            with BytesIO() as output:
                gl.media_manager.generate_svg_thumbnail(path, MDI_SIZE, MDI_SIZE).save(output, format='PNG')  # You can choose other formats like 'JPEG'
                memory_input_stream = Gio.MemoryInputStream.new_from_data(output.getvalue(), None)
                self.pixbuf = GdkPixbuf.Pixbuf.new_from_stream_at_scale(memory_input_stream, width=MDI_SIZE, height=MDI_SIZE,
                                                                        preserve_aspect_ratio=True)
            self.picture.set_size_request(MDI_SIZE, MDI_SIZE)
        else:
            self.pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(path, width=250, height=180,
                                                                  preserve_aspect_ratio=True)
            self.picture.set_size_request(250, 180)

        self.picture.set_pixbuf(self.pixbuf)

    def set_text(self, text:str):
        self.label.set_text(text)

    def on_click_info(self, *args):
        pass

    def on_click_remove(self, *args):
        pass