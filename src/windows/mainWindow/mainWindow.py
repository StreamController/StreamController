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
from gi.repository import Gtk, Adw, GLib, Gio
GLib.threads_init()

# Import Python modules
from loguru import logger as log

# Import own modules
from src.windows.mainWindow.elements.leftArea import LeftArea
from src.windows.mainWindow.elements.RightArea.RightArea import RightArea
from src.windows.mainWindow.headerBar import HeaderBar
from src.GtkHelper import get_deepest_focused_widget, get_deepest_focused_widget_with_attr

# Import globals
import globals as gl

class MainWindow(Gtk.ApplicationWindow):
    def __init__(self, deck_manager, **kwargs):
        super().__init__(**kwargs)
        self.deck_manager = deck_manager
        self.set_size_request(1000, 600)
        self.build()
        self.init_actions()

    @log.catch
    def build(self):
        log.trace("Building main window")

        self.mainBox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, hexpand=True)
        self.set_child(self.mainBox)

        self.mainPaned = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL, hexpand=True, vexpand=True)
        self.mainBox.append(self.mainPaned)

        self.leftArea = LeftArea(self, deck_manager=self.deck_manager, margin_end=3, width_request=500, margin_bottom=10)
        self.mainPaned.set_start_child(self.leftArea)

        self.rightArea = RightArea(main_window=self, margin_start=4, width_request=300, margin_end=4)
        self.mainPaned.set_end_child(self.rightArea)

        # Add header bar
        self.header_bar = HeaderBar(self.deck_manager, self, self.leftArea.deck_stack)
        self.set_titlebar(self.header_bar)

    def init_actions(self):
        # Copy paste actions
        self.copy_action = Gio.SimpleAction.new("copy", None)
        self.cut_action = Gio.SimpleAction.new("cut", None)
        self.paste_action = Gio.SimpleAction.new("paste", None)
        self.remove_action = Gio.SimpleAction.new("remove", None)

        # Connect actions
        self.copy_action.connect("activate", self.on_copy)
        self.cut_action.connect("activate", self.on_cut)
        self.paste_action.connect("activate", self.on_paste)
        self.remove_action.connect("activate", self.on_remove)

        # Set accels
        gl.app.set_accels_for_action("win.copy", ["<Primary>c"])
        gl.app.set_accels_for_action("win.cut", ["<Primary>x"])
        gl.app.set_accels_for_action("win.paste", ["<Primary>v"])
        gl.app.set_accels_for_action("win.remove", ["Delete"])

        # Add actions to window
        self.add_action(self.copy_action)
        self.add_action(self.cut_action)
        self.add_action(self.paste_action)
        self.add_action(self.remove_action)

    def on_copy(self, *args):
        child = get_deepest_focused_widget_with_attr(self, "on_copy")
        if hasattr(child, "on_copy"):
            child.on_copy()

    def on_cut(self, *args):
        child = get_deepest_focused_widget_with_attr(self, "on_cut")
        if hasattr(child, "on_cut"):
            child.on_cut()

    def on_paste(self, *args):
        child = get_deepest_focused_widget_with_attr(self, "on_paste")
        if hasattr(child, "on_paste"):
            child.on_paste()

    def on_remove(self, *args):
        child = get_deepest_focused_widget_with_attr(self, "on_remove")
        if hasattr(child, "on_remove"):
            child.on_remove()