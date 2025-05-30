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

class OfficialBadge(Gtk.Button):
    def __init__(self, *args, **kwargs):
        super().__init__(label=gl.lm.get("store.badges.official"), *args, **kwargs)

class VerifiedBadge(Gtk.Button):
    def __init__(self, *args, **kwargs):
        super().__init__(label=gl.lm.get("store.badges.verified"), *args, **kwargs)