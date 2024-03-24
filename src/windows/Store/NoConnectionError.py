"""
Year: 2024

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
any later version.

This programm comes with ABSOLUTELY NO WARRANTY!

You should have received a copy of the GNU General Public License
along with this program. If not, see <https://www.gnu.org/licenses/>.
"""
# Import gtk modules
from operator import iconcat
import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk

class NoConnectionError(Gtk.Box):
    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.VERTICAL,
                         halign=Gtk.Align.CENTER, valign=Gtk.Align.CENTER)

        # self.icon = Gtk.Picture(icon_name="network-offline")
        self.icon = Gtk.Image(icon_name="network-offline", icon_size=200, pixel_size=200,
                              margin_bottom=30)
        self.append(self.icon)

        self.label = Gtk.Label(label="No Connection", css_classes=["error-label"])
        self.append(self.label)