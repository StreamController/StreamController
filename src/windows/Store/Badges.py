"""
Year: 2023

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
any later version.

This programm comes with ABSOLUTELY NO WARRANTY!

You should have received a copy of the GNU General Public License
along with this program. If not, see <https://www.gnu.org/licenses/>.
"""
import os

# Import gtk modules
import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk

# Import globals
import globals as gl
from gi.repository import GdkPixbuf

class Badge:
    def __init__(self, badge_name, tooltip=None):
        path = os.path.join(gl.top_level_dir, "Assets", "images", "badges", badge_name)
        size = 128

        pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_size(path, width=size, height=size)
        self.image = Gtk.Image.new_from_pixbuf(pixbuf)

        self.image.set_valign(Gtk.Align.START)
        self.image.set_halign(Gtk.Align.START)
        self.image.set_margin_end(5)

        self.image.set_tooltip_text(tooltip)

    def set_enabled(self, enable):
        self.image.set_visible(enable)