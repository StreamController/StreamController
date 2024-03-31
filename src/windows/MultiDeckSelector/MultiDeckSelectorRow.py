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
# Import gtk modules
from operator import call
import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw

from src.windows.MultiDeckSelector.MultiDeckSelector import MultiDeckSelector

# Import globals
import globals as gl

class MultiDeckSelectorRow(Adw.ActionRow):
    def __init__(self, source_window: Gtk.ApplicationWindow, title: str, subtitle: str, selected_deck_serials: list[str] = [], callback: callable = None):
        super().__init__(title = title, subtitle = subtitle, activatable=True)

        self.source_window = source_window
        self.selected_deck_serials = selected_deck_serials
        self.callback = callback

        self.multi_deck_selector: MultiDeckSelector = None

        self.build()

        self.connect("activated", self.on_activated)

    def build(self):
        self.suffix_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.add_suffix(self.suffix_box)

        self.suffix_label = Gtk.Label()
        self.set_label(len(self.selected_deck_serials))
        self.suffix_box.append(self.suffix_label)

        self.arrow_icon = Gtk.Image(icon_name="com.core447.StreamController-go-next-symbolic")
        self.suffix_box.append(self.arrow_icon)

    def on_activated(self, widget):
        if self.multi_deck_selector is None:
            self.multi_deck_selector = MultiDeckSelector(
                application=gl.app,
                source_window=self.source_window,
                selected_deck_serials=self.selected_deck_serials,
                callback=self.change_callback
            )
        
        self.multi_deck_selector.present()

    def set_label(self, n_selected_decks: int):
        self.suffix_label.set_label(f"{n_selected_decks} {gl.lm.get('multi-deck-selector.selected')}")

    def change_callback(self, serial_number: str, state: bool):
        n_selected_decks = self.multi_deck_selector.get_n_selected_decks()
        self.set_label(n_selected_decks)

        if callable(self.callback):
            self.callback(serial_number, state)