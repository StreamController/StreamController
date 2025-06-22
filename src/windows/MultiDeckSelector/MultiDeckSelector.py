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

# Import globals
import globals as gl

class MultiDeckSelector(Gtk.ApplicationWindow):
    def __init__(self, application: Gtk.Application, source_window: Gtk.ApplicationWindow,
                 selected_deck_serials: list[str] = [], callback: callable = None):
        super().__init__(application=application,
                         title=gl.lm.get("multi-deck-selector.title"),
                         transient_for=source_window,
                         modal=True,
                         default_width=350, default_height=350)
        
        self.source_window = source_window
        self.selected_deck_serials = selected_deck_serials
        self.callback = callback
        self.rows: list[DeckRow] = []
        self.build()
        self.load_decks()
        self.set_selected_deck_serials(self.selected_deck_serials)

    def build(self):
        self.header = Adw.HeaderBar(css_classes=["flat"])
        self.set_titlebar(self.header)

        self.scrolled_window = Gtk.ScrolledWindow(hexpand=True, vexpand=True,
                                                  margin_start=7, margin_end=7, margin_top=7, margin_bottom=7)
        self.set_child(self.scrolled_window)

        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.scrolled_window.set_child(self.main_box)

        self.deck_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, vexpand=True)
        self.main_box.append(self.deck_box)

        self.not_attached_label = Gtk.Label(css_classes=["dim-label"], margin_bottom=3, margin_top=3)
        self.main_box.append(self.not_attached_label)

    def load_decks(self):
        for controller in gl.deck_manager.get_physical_controllers():
            serial_number, name = gl.app.main_win.leftArea.deck_stack.get_page_attributes(controller)

            row = DeckRow(self, name, serial_number, False)
            self.rows.append(row)
            self.deck_box.append(row)

    def call_callback(self, serial_number: str, state: bool):
        if callable(self.callback):
            self.callback(serial_number, state)

    def get_n_selected_decks(self) -> int:
        """
        Returns the number of selected decks based on the widgets
        """
        n = 0
        for row in self.rows:
            if row.get_active():
                n += 1
        return n
    
    def set_selected_deck_serials(self, serials: list[str]):
        for row in self.rows:
            if row.deck_serial_number in serials:
                row.set_active(True)
            else:
                row.set_active(False)

        n_not_connected = 0
        connected = gl.deck_manager.get_physical_deck_serials()
        for serial in serials:
            if serial not in connected:
                n_not_connected += 1

        self.not_attached_label.set_label(f"{n_not_connected} deck(s) not connected")            
        self.not_attached_label.set_visible(n_not_connected > 0)


class DeckRow(Gtk.CheckButton):
    def __init__(self, selector: MultiDeckSelector, deck_name: str, deck_serial_number: str, active: bool = False):
        super().__init__(label=deck_name, css_classes=["multi-deck-selector-label"], active=active, margin_bottom=3)
        self.deck_name = deck_name
        self.selector = selector
        self.deck_serial_number = deck_serial_number

        self.connect("toggled", self.on_toggled)

    def on_toggled(self, button: Gtk.CheckButton):
        self.selector.call_callback(self.deck_serial_number, button.get_active())