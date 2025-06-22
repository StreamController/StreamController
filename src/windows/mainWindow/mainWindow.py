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

from src.backend.DeckManagement.HelperMethods import recursive_hasattr


gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, GLib, Gio, Gdk
GLib.threads_init()

# Import Python modules
from loguru import logger as log

# Import own modules
from src.windows.mainWindow.elements.KeepRunningDialog import KeepRunningDialog
from src.windows.mainWindow.elements.leftArea import LeftArea
from src.windows.mainWindow.elements.Sidebar.Sidebar import Sidebar
from src.windows.mainWindow.headerBar import HeaderBar
from GtkHelper.GtkHelper import get_deepest_focused_widget, get_deepest_focused_widget_with_attr
from src.windows.mainWindow.elements.NoPagesError import NoPagesError
from src.windows.mainWindow.elements.NoDecksError import NoDecksError
from src.windows.mainWindow.deckSwitcher import DeckSwitcher
from src.windows.mainWindow.elements.PageSelector import PageSelector
from src.windows.mainWindow.elements.HeaderHamburgerMenuButton import HeaderHamburgerMenuButton
from src.backend.DeckManagement.DeckController import DeckController
from src.backend.PageManagement.Page import Page


# Import globals
import globals as gl

class MainWindow(Adw.ApplicationWindow):
    def __init__(self, deck_manager, **kwargs):
        gl.app.main_win = self
        super().__init__(**kwargs)
        self.deck_manager = deck_manager

        # Store copied stuff
        self.key_dict = {}

        # Add tasks to run if build is complete
        self.on_finished: list = []

        self.build()
        self.init_actions()

        self.set_size_request(800, 700)
        self.set_default_size(1400, 900)
        self.connect("close-request", self.on_close)

        self.key_clipboard: Gdk.Clipboard = Gdk.Display.get_default().get_clipboard()

        if gl.cli_args.devel:
            self.add_css_class("devel")

    def on_close(self, *args, **kwargs):
        keep_running = gl.settings_manager.get_app_settings().get("system", {}).get("keep-running")
        if keep_running is None:
            dialog = KeepRunningDialog(self, self.on_close)
            dialog.present()
        else:
            # self._on_close(keep_running)
            self.hide()
            if not keep_running:
                GLib.idle_add(gl.app.on_quit)

        return True

    def _on_close(self, keep_running: bool) -> None:
        self.hide()
        if not keep_running:
            gl.app.on_quit()
        return True

    @log.catch
    def build(self):
        #TODO: Put the objects in classes
        log.trace("Building main window")
        self.split_view = Adw.NavigationSplitView()
        self.set_content(self.split_view)

        self.content_page = Adw.NavigationPage(title="StreamController")
        self.split_view.set_content(self.content_page)

        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, hexpand=True)
        self.content_page.set_child(self.main_box)

        # Add a main stack containing the normal ui and error pages
        self.main_stack = Gtk.Stack(hexpand=True, vexpand=True)
        self.main_box.append(self.main_stack)

        # Add the main stack as the content widget of the split view
        self.split_view.set_show_content(self.content_page)

        # Main toast
        self.toast_overlay = Adw.ToastOverlay()
        self.main_stack.add_titled(self.toast_overlay, "main", "Main")

        # Add a box for the main content (right side)
        self.content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, hexpand=True)
        self.toast_overlay.set_child(self.content_box)

        self.leftArea = LeftArea(self, deck_manager=self.deck_manager, margin_end=3, width_request=500, margin_bottom=10)
        self.content_box.append(self.leftArea)

        self.sidebar = Sidebar(main_window=self, margin_start=4, width_request=300, margin_end=4)
        # self.mainPaned.set_end_child(self.sidebar)
        self.split_view.set_sidebar(self.sidebar)
        self.split_view.set_sidebar_width_fraction(0.4)
        self.split_view.set_min_sidebar_width(450)
        self.split_view.set_max_sidebar_width(600)

        # Add header
        self.header = Adw.HeaderBar(css_classes=["flat"], show_back_button=False)
        self.main_box.prepend(self.header)

        # Add deck switcher to the header bar
        self.deck_switcher = DeckSwitcher(self)
        self.deck_switcher.switcher.set_stack(self.leftArea.deck_stack)
        self.header.set_title_widget(self.deck_switcher)

        # Add menu button to the header bar
        self.menu_button = HeaderHamburgerMenuButton(main_window=self)
        self.header.pack_end(self.menu_button)

        # Add sidebar toggle button to the header bar
        self.sidebar_toggle_button = Gtk.ToggleButton(icon_name="sidebar-show-symbolic", active=True)
        self.sidebar_toggle_button.connect("toggled", self.on_toggle_sidebar)
        # self.header.pack_start(self.sidebar_toggle_button)


        # Error pages
        self.no_pages_error = NoPagesError()
        self.main_stack.add_titled(self.no_pages_error, "no-pages-error", "No Pages Error")

        self.no_decks_error = NoDecksError()
        self.main_stack.add_titled(self.no_decks_error, "no-decks-error", "No Decks Error")

        self.do_after_build_tasks()
        self.check_for_errors()

        gl.tray_icon.initialize(self)
        

    def on_toggle_sidebar(self, button):
        return
        if button.get_active():
            self.split_view.set_collapsed(False)
        else:
            self.split_view.set_collapsed(True)

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
        self.add_accel_actions()


    def add_accel_actions(self):
        return
        self.add_action(self.copy_action)
        self.add_action(self.cut_action)
        self.add_action(self.paste_action)
        self.add_action(self.remove_action)

    def remove_accel_actions(self):
        return
        self.remove_action(self.copy_action)
        self.remove_action("win.cut")
        self.remove_action("win.paste")
        self.remove_action("win.remove")


    def change_ui_to_no_connected_deck(self):
        if not hasattr(self, "leftArea"):
            self.add_on_finished(self.change_ui_to_no_connected_deck)
            return
        
        self.leftArea.show_no_decks_error()

    def change_ui_to_connected_deck(self):
        if not hasattr(self, "leftArea"):
            self.add_on_finished(self.change_ui_to_connected_deck)
            return
        
        self.leftArea.hide_no_decks_error()
        self.deck_switcher.set_show_switcher(True)

    def set_main_error(self, error: str=None):
        """
        error: str
            no-decks: Shows the no decks available error
            no-pages: Shows the no pages available error
            None: Goes back to normal mode
        """
        if error is None:
            GLib.idle_add(self.main_stack.set_visible_child, self.toast_overlay)
            GLib.idle_add(self.deck_switcher.set_show_switcher, True)
            GLib.idle_add(self.split_view.set_collapsed, False)
            GLib.idle_add(self.sidebar_toggle_button.set_visible, True)
            GLib.idle_add(self.menu_button.set_optional_actions_state, True)
            GLib.idle_add(self.split_view.set_collapsed, False)
            return
        
        elif error == "no-decks":
            GLib.idle_add(self.main_stack.set_visible_child, self.no_decks_error)
            GLib.idle_add(self.deck_switcher.set_label_text, gl.lm.get("deck-switcher-no-decks"))

        elif error == "no-pages":
            GLib.idle_add(self.main_stack.set_visible_child, self.no_pages_error)
            GLib.idle_add(self.deck_switcher.set_label_text, gl.lm.get("errors.no-page.header"))

        GLib.idle_add(self.deck_switcher.set_show_switcher, False)
        GLib.idle_add(self.sidebar_toggle_button.set_visible, False)
        GLib.idle_add(self.menu_button.set_optional_actions_state, False)
        GLib.idle_add(self.split_view.set_collapsed, True)

    def check_for_errors(self):
        if len(gl.deck_manager.get_all_controllers()) == 0:
            self.set_main_error("no-decks")

        elif len(gl.page_manager.get_page_names(add_custom_pages=False)) == 0:
            self.set_main_error("no-pages")

        else:
            self.set_main_error(None)

    def add_on_finished(self, task: callable) -> None:
        if not callable(task):
            return
        if task in self.on_finished:
            return
        self.on_finished.append(task)


    def reload_sidebar(self):
        if not hasattr(self, "sidebar"):
            self.add_on_finished(self.reload_sidebar)
            return
        
        self.sidebar.update()

    def do_after_build_tasks(self):
        for task in self.on_finished:
            if callable(task):
                task()

    def on_copy(self, *args):
        child = get_deepest_focused_widget_with_attr(self, "on_copy")
        if hasattr(child, "on_copy"):
            child.on_copy()

        return False

    def on_cut(self, *args):
        child = get_deepest_focused_widget_with_attr(self, "on_cut")
        if hasattr(child, "on_cut"):
            child.on_cut()

        return False

    def on_paste(self, *args):
        child = get_deepest_focused_widget_with_attr(self, "on_paste")
        if hasattr(child, "on_paste"):
            child.on_paste()

        return False

    def on_remove(self, *args):
        child = get_deepest_focused_widget_with_attr(self, "on_remove")
        if hasattr(child, "on_remove"):
            child.on_remove()

        return False

    def show_info_toast(self, text: str) -> None:
        toast = Adw.Toast(
            title=text,
            timeout=3,
            priority=Adw.ToastPriority.NORMAL
        )
        self.toast_overlay.add_toast(toast)

    def get_active_controller(self) -> DeckController:
        if not recursive_hasattr(self, "leftArea.deck_stack"): return
        visible_child = self.leftArea.deck_stack.get_visible_child()
        if visible_child is None:
            return
        return visible_child.deck_controller
    
    def get_active_page(self) -> Page:
        controller = self.get_active_controller()
        if controller is None:
            return gl.page_manager.dummy_page
        if hasattr(controller, "active_page"):
            return controller.active_page


class PageManagerNavPage(Adw.NavigationPage):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.build()

    def build(self):
        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, hexpand=True, margin_top=30)
        self.set_child(self.main_box)

        for i in range(10):
            self.main_box.append(PageRow(window=None))


class PageRow(Gtk.ListBoxRow):
    def __init__(self, window: MainWindow):
        self.window = window
        super().__init__()
        self.set_margin_bottom(4)
        self.set_margin_start(50)
        self.set_margin_end(50)

        self.main_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, hexpand=True)
        self.set_child(self.main_box)

        self.main_button = Gtk.Button(hexpand=True, height_request=30,
                                      label="Page Name",
                                      css_classes=["no-round-right"])
        self.main_box.append(self.main_button)

        self.main_box.append(Gtk.Separator(orientation=Gtk.Orientation.VERTICAL))

        self.config_button = Gtk.Button(height_request=30,
                                        icon_name="view-more",
                                        css_classes=["no-round-left"])
        self.config_button.connect("clicked", self.on_config)
        self.main_box.append(self.config_button)

    def on_config(self, button):
        return
        context = KeyButtonContextMenu(self, self.window)
        context.popup()