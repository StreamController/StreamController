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
from GtkHelper.GtkHelper import get_deepest_focused_widget, get_deepest_focused_widget_with_attr
from src.windows.mainWindow.elements.NoPagesError import NoPagesError
from src.windows.mainWindow.elements.NoDecksError import NoDecksError


# Import globals
import globals as gl

class MainWindow(Gtk.ApplicationWindow):
    def __init__(self, deck_manager, **kwargs):
        super().__init__(**kwargs)
        self.deck_manager = deck_manager
        self.set_size_request(1000, 600)

        # Store copied stuff
        self.key_dict = {}

        # Add tasks to run if build is complete
        self.on_finished: list = []

        self.build()
        self.init_actions()

    @log.catch
    def build(self):
        log.trace("Building main window")

        self.main_stack = Gtk.Stack(hexpand=True, vexpand=True)
        self.set_child(self.main_stack)

        self.mainBox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, hexpand=True)
        self.main_stack.add_titled(self.mainBox, "main", "Main")

        self.mainPaned = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL, hexpand=True, vexpand=True)
        self.mainBox.append(self.mainPaned)

        self.leftArea = LeftArea(self, deck_manager=self.deck_manager, margin_end=3, width_request=500, margin_bottom=10)
        self.mainPaned.set_start_child(self.leftArea)

        self.rightArea = RightArea(main_window=self, margin_start=4, width_request=300, margin_end=4)
        self.mainPaned.set_end_child(self.rightArea)

        # Add header bar
        self.header_bar = HeaderBar(self.deck_manager, self, self.leftArea.deck_stack)
        self.set_titlebar(self.header_bar)

        # Error pages
        self.no_pages_error = NoPagesError()
        self.main_stack.add_titled(self.no_pages_error, "no-pages-error", "No Pages Error")

        self.no_decks_error = NoDecksError()
        self.main_stack.add_titled(self.no_decks_error, "no-decks-error", "No Decks Error")

        self.do_after_build_tasks()

        self.check_for_errors()

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


    def change_ui_to_no_connected_deck(self):
        if not hasattr(self, "leftArea"):
            self.on_finished.append(self.change_ui_to_no_connected_deck)
            return
        
        self.leftArea.show_no_decks_error()
        self.header_bar.config_button.set_visible(False)
        self.header_bar.page_selector.set_visible(False)

    def change_ui_to_connected_deck(self):
        if not hasattr(self, "leftArea"):
            self.on_finished.append(self.change_ui_to_connected_deck)
            return
        
        self.leftArea.hide_no_decks_error()
        self.header_bar.config_button.set_visible(True)
        self.header_bar.page_selector.set_visible(True)

    def set_main_error(self, error: str=None):
        """"
        error: str
            no-decks: Shows the no decks available error
            no-pages: Shows the no pages available error
            None: Goes back to normal mode
        """
        if error is None:
            self.main_stack.set_visible_child(self.mainBox)
            self.header_bar.config_button.set_visible(True)
            self.header_bar.page_selector.set_visible(True)
            self.header_bar.deckSwitcher.set_show_switcher(True)
            return
        
        elif error == "no-decks":
            self.main_stack.set_visible_child(self.no_decks_error)

        elif error == "no-pages":
            self.main_stack.set_visible_child(self.no_pages_error)

        self.header_bar.config_button.set_visible(False)
        self.header_bar.page_selector.set_visible(False)
        self.header_bar.deckSwitcher.set_show_switcher(False)

    def check_for_errors(self):
        if len(gl.deck_manager.deck_controller) == 0:
            self.set_main_error("no-decks")

        elif len(gl.page_manager.get_page_names()) == 0:
            self.set_main_error("no-pages")

        else:
            self.set_main_error(None)


    def reload_right_area(self):
        if not hasattr(self, "rightArea"):
            self.on_finished.append(self.reload_right_area)
            return
        
        self.rightArea.load_for_coords(self.rightArea.active_coords)

    def do_after_build_tasks(self):
        for task in self.on_finished:
            if callable(task):
                task()

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