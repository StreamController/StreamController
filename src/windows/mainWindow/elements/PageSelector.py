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
from gi.repository import Gtk, Adw, Gio, GObject, Pango

# Import Python modules
from loguru import logger as log
import os

# Import globas
import globals as gl

# Import own modules
from src.windows.PageManager.PageManager import PageManager
from src.Signals import Signals

class PageSelector(Gtk.Box):
    def __init__(self, main_window, page_manager, **kwargs):
        self.main_window = main_window
        self.page_manager = page_manager
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL, **kwargs)
        self.build()

    def build(self):
        # Label
        self.label = Gtk.Label(label=gl.lm.get("header-page-selector-page-label"), margin_start=3, margin_end=7, css_classes=["bold"])
        self.append(self.label)

        # Right area
        self.sidebar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, css_classes=["linked"])
        self.append(self.sidebar)

        # Dropdown
        self.pages_model = Gtk.ListStore.new([str, str])
        self.drop_down = Gtk.ComboBox.new_with_model(self.pages_model)
        self.drop_down.set_css_classes(["header-page-dropdown"])
        self.drop_down.set_hexpand(False)

        self.renderer_text = Gtk.CellRendererText(ellipsize=Pango.EllipsizeMode.END, ellipsize_set=True)
        self.drop_down.pack_start(self.renderer_text, True)
        # Use first column for text
        self.drop_down.add_attribute(self.renderer_text, "text", 0)

        # self.drop_down.set_model(self.pages_model)
        self.drop_down.set_tooltip_text(gl.lm.get("header-page-selector-drop-down-hint"))
        self.drop_down.connect("changed", self.on_change_page)
        self.update()
        self.sidebar.append(self.drop_down)

        # Settings button
        self.open_manager_button = Gtk.Button(icon_name="folder-open-symbolic", tooltip_text=gl.lm.get("header-page-selector-page-manager-hint"))
        self.open_manager_button.connect("clicked", self.on_click_open_page_manager)
        self.sidebar.append(self.open_manager_button)

        gl.signal_manager.connect_signal(signal=Signals.ChangePage, callback=self.update_selected)
        gl.signal_manager.connect_signal(signal=Signals.PageRename, callback=self.update)
        gl.signal_manager.connect_signal(signal=Signals.PageAdd, callback=self.update)
        gl.signal_manager.connect_signal(signal=Signals.PageDelete, callback=self.update)
    
    def update(self, *args, **kwargs):
        self.disconnect_change_signal()
        pages = self.page_manager.get_pages()
        pages.sort()
        # self.clear_model()
        self.pages_model.clear()
        for page in pages:
            display_name = os.path.splitext(os.path.basename(page))[0]
            self.pages_model.append([display_name, page])  # Append a tuple
            
        self.update_selected()

        # self.connect("notify::selected", self.on_change_page)
        self.connect_change_signal()

    def clear_model(self):
        self.pages_model.clear()
        return
        for i in range(self.pages_model.get_n_items()):
            self.pages_model.remove(0)

    def set_selected(self, page_path: str):
        for i, row in enumerate(self.pages_model):
            if row[1] == page_path:
                self.drop_down.set_active(i)
                return
            
    def update_selected(self, *args, **kwargs):
        child = self.main_window.leftArea.deck_stack.get_visible_child()
        if child is None:
            self.drop_down.set_sensitive(False)
            return
        else:
            self.drop_down.set_sensitive(True)
        active_controller = child.deck_controller
        page = active_controller.active_page
        if page is None:
            return
        page_path = page.json_path
        self.set_selected(page_path)

    def on_change_page(self, drop_down, *args):
        active_child = self.main_window.leftArea.deck_stack.get_visible_child()
        if active_child is None:
            return
        
        active_controller = active_child.deck_controller
        if active_controller is None:
            return
        
        page_path = self.pages_model[drop_down.get_active()][1]
        page = gl.page_manager.get_page(path=page_path, deck_controller = active_controller)
        log.info(f"Load page: {page}")
        active_controller.load_page(page)

    def on_click_open_page_manager(self, button):
        if gl.page_manager_window is not None:
            gl.page_manager_window.present()
        gl.page_manager_window = PageManager(main_win=gl.app.main_win)
        gl.page_manager_window.present()

    def disconnect_change_signal(self):
        try:
            self.drop_down.disconnect_by_func(self.on_change_page)
        except:
            pass

    def connect_change_signal(self):
        self.drop_down.connect("changed", self.on_change_page)