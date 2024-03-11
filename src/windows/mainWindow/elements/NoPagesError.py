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
import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw

# Import own modules
from GtkHelper.GtkHelper import EntryDialog
import os

# Import Python modules
from loguru import logger as log

# Import globals
import globals as gl

# Import signals
from src.Signals import Signals

class NoPagesError(Gtk.Box):
    """
    This error gets shown if there are no pages registered/available
    """
    def __init__(self):
        super().__init__(
            orientation=Gtk.Orientation.VERTICAL,
            halign=Gtk.Align.CENTER,
            valign=Gtk.Align.CENTER,
            homogeneous=False,
            hexpand=True, vexpand=True
        )

        self.build()

    def build(self):
        self.no_pages_label = Gtk.Label(label="No Pages Available", css_classes=["error-label"])
        self.append(self.no_pages_label)

        self.create_new_button = Gtk.Button(label="Create New", margin_top=60, css_classes=["error-resolve-button"],
                                            hexpand=False, margin_start=60, margin_end=60)
        self.create_new_button.connect("clicked", self.on_create_new)
        self.append(self.create_new_button)

    def on_create_new(self, button):
        dial = EntryDialog(parent_window=gl.app.main_win, dialog_title="Add Page", entry_heading="Page name:", default_text="page",
                           forbid_answers=gl.page_manager.get_page_names())
        dial.show(self.add_page_callback)

    def add_page_callback(self, name:str):
        path = os.path.join(gl.DATA_PATH, "pages", f"{name}.json")
        gl.page_manager.add_page(name)

        # Notify plugin actions
        gl.plugin_manager.trigger_signal(signal= Signals.PageAdd, path= path)

        gl.app.main_win.check_for_errors()

        active_controller = gl.app.main_win.leftArea.deck_stack.get_visible_child().deck_controller
        if active_controller is None:
            return
        
        active_controller.load_default_page()