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
# Import gtk modules
import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk

# Import globals
import globals as gl

class Badge(Gtk.Button):
    def __init__(self, label: str, tooltip: str = None, *args, **kwargs):
        super().__init__(
            label=gl.lm.get(label),
            *args, **kwargs
        )
        self.set_tooltip(tooltip)

    def set_tooltip(self, tooltip: str):
        if tooltip:
            self.set_has_tooltip(True)
        else:
            self.set_has_tooltip(False)
        self.set_tooltip_text(gl.lm.get(tooltip))