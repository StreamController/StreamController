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

from src.windows.Store.StorePageSection import StorePageSection

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, GLib

# Import python modules
from fuzzywuzzy import fuzz
import threading
from loguru import logger as log

# Import own modules
from src.windows.Store.InfoPage import InfoPage
from GtkHelper.GtkHelper import ErrorPage
from src.windows.Store.NoConnectionError import NoConnectionError
from packaging import version

# Typing
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from src.windows.Store.Store import Store

# Import globals
import globals as gl

class StorePage(Gtk.Stack):
    def __init__(self, store: "Store"):
        super().__init__()
        self.set_hexpand(True)
        self.set_vexpand(True)
        self.set_margin_start(15)
        self.set_margin_end(15)
        self.set_margin_top(15)
        self.set_margin_bottom(15)
        self.set_transition_duration(200)
        self.set_transition_type(Gtk.StackTransitionType.SLIDE_LEFT_RIGHT)

        self.store = store

        self.build()

    def build(self):
        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, hexpand=True)
        self.add_titled(self.main_box, "Store", "Store")

        self.section_stack = Gtk.Stack(vexpand=True)
        self.main_box.append(self.section_stack)

        self.compatible_section = StorePageSection()
        self.incompatible_section = StorePageSection()
        self.incompatible_section.nothing_here.set_icon_name("face-smile-symbolic")


        self.section_switcher = Gtk.StackSwitcher(stack=self.section_stack, margin_bottom=15)
        self.main_box.prepend(self.section_switcher)
        
        self.section_stack.add_titled(self.compatible_section, "Compatible", "Compatible")
        self.section_stack.add_titled(self.incompatible_section, "Incompatible", "Incompatible")
        self.section_stack.set_visible_child(self.compatible_section)

        self.loading_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, hexpand=True, vexpand=True,
                                   visible=False, valign=Gtk.Align.CENTER)
        self.main_box.append(self.loading_box)

        self.spinner = Gtk.Spinner(spinning=False)
        self.loading_box.append(self.spinner)

        self.loading_text = Gtk.Label(label=gl.lm.get("store.page.loading-spinner.label"))
        self.loading_box.append(self.loading_text)

        # Info page
        self.info_page = InfoPage(self)
        self.add_titled(self.info_page, "Info", "Info")

        # Error page
        self.no_connection_page = NoConnectionError()
        self.add_titled(self.no_connection_page, "Error", "Error")

    def set_loading(self):
        GLib.idle_add(self.section_stack.set_visible, False)
        # GLib.idle_add(self.bottom_box.set_visible, False)
        GLib.idle_add(self.loading_box.set_visible, True)
        # threading.Thread(target=self.spinner.set_spinning, args=(True,), name="spinner_thread").start()
        GLib.idle_add(self.spinner.set_spinning, True)
        GLib.idle_add(self.section_switcher.set_visible, False)

    def set_loaded(self):
        GLib.idle_add(self.section_stack.set_visible, True)
        # GLib.idle_add(self.bottom_box.set_visible, True)
        GLib.idle_add(self.loading_box.set_visible, False)
        GLib.idle_add(self.spinner.set_spinning, False)
        GLib.idle_add(self.section_switcher.set_visible, True)
        GLib.idle_add(self.hide_stack_switcher_if_all_compatible)

    def hide_stack_switcher_if_all_compatible(self):
        if not self.incompatible_section.are_items_present():
            self.section_switcher.set_visible(False)

    def set_info_visible(self, visible:bool):
        if visible:
            self.set_visible_child(self.info_page)
            self.store.back_button.set_visible(True)
        else:
            self.set_visible_child(self.main_box)
            self.store.back_button.set_visible(False)

    def show_connection_error(self):
        self.set_visible_child(self.no_connection_page)

    def hide_connection_error(self):
        self.set_visible_child(self.main_box)

    def check_required_version(self, app_version_to_check: str, is_min_app_version: bool = False):
        if is_min_app_version:
            if app_version_to_check is None:
                return True
            min_version = version.parse(app_version_to_check)
            app_version = version.parse(gl.app_version)

            return min_version < app_version