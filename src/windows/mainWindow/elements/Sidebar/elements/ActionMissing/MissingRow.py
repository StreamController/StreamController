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
from gi.repository import Gtk, Adw, Gdk, GLib, Pango

import asyncio
import threading
import globals as gl
from loguru import logger as log

class MissingRow(Adw.PreferencesRow):
    def __init__(self, action_id:str, page_coords:str, index:int, state:int,
                 install_label: str,
                 install_failed_label: str,
                 installing_label: str):
        super().__init__(css_classes=["no-padding"])
        self.action_id = action_id
        self.page_coords = page_coords
        self.state = state
        self.index = index
        self.install_label = install_label
        self.install_failed_label = install_failed_label
        self.installing_label = installing_label

        self.main_overlay = Gtk.Overlay()
        self.set_child(self.main_overlay)

        self.main_button = Gtk.Button(hexpand=True, css_classes=["invisible"])
        self.main_button.connect("clicked", self.on_click)
        self.main_overlay.set_child(self.main_button)

        self.main_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, hexpand=True,
                                margin_bottom=15, margin_top=15)
        self.main_button.set_child(self.main_box)

        # Counter part for the button on the right - other wise the label is not centered
        self.main_box.append(Gtk.Box(width_request=50))
    
        self.center_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, hexpand=True)
        self.main_box.append(self.center_box)

        self.spinner = Gtk.Spinner(spinning=False, margin_bottom=5, visible=False)
        self.center_box.append(self.spinner)

        self.label = Gtk.Label(label=self.install_label, xalign=Gtk.Align.CENTER, vexpand=True, valign=Gtk.Align.CENTER)
        self.center_box.append(self.label)

        self.button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, width_request=50)
        self.main_box.append(self.button_box)

        self.remove_button = Gtk.Button(icon_name="user-trash-symbolic", vexpand=False, halign=Gtk.Align.END, css_classes=["destructive-action", "no-rounded-corners"], margin_end=0,
                                        tooltip_text="Remove this action", overflow=Gtk.Overflow.HIDDEN) # alternative icon: edit-delete-remove
        self.remove_button.connect("clicked", self.on_remove_click)
        # self.button_box.append(self.remove_button)
        self.main_overlay.add_overlay(self.remove_button)

    def on_click(self, button):
        self.spinner.set_visible(True)
        self.spinner.start()
        self.label.set_text(self.installing_label)

        # Run in thread to allow the ui to update
        threading.Thread(target=self.install, name="asset_install_thread").start()

    @log.catch
    def install(self):
        # Get missing plugin from id
        plugin = asyncio.run(gl.store_backend.get_plugin_for_id(self.action_id.split("::")[0]))
        if plugin is None:
            self.show_install_error()
            return
        # Install plugin
        success = asyncio.run(gl.store_backend.install_plugin(plugin))
        if success == 404:
            self.show_install_error()
            return
        
        # Reset ui
        GLib.idle_add(self.spinner.set_visible, False)
        GLib.idle_add(self.spinner.stop)
        GLib.idle_add(self.label.set_text, self.install_label)

        # Reload pages
        

    def show_install_error(self):
        GLib.idle_add(self.spinner.set_visible, False)
        GLib.idle_add(self.spinner.stop)
        GLib.idle_add(self.label.set_text, self.install_failed_label)
        GLib.idle_add(self.remove_css_class, "error")
        GLib.idle_add(self.set_sensitive, False)

        # Hide error after 3s
        threading.Timer(3, self.hide_install_error).start()

    def hide_install_error(self):
        self.label.set_text(self.install_label)
        self.remove_css_class("error")
        self.set_sensitive(True)
        self.main_button.set_sensitive(True)

    def on_remove_click(self, button):
        controller = gl.app.main_win.leftArea.deck_stack.get_visible_child().deck_controller
        page = controller.active_page

        # Remove from action objects
        del page.action_objects[self.page_coords][self.index]

        # Remove from page json
        page.dict["keys"][self.page_coords]["actions"].pop(self.index)
        page.save()

        # Reload configurator ui
        gl.app.main_win.sidebar.key_editor.action_editor.load_for_coords(self.page_coords.split("x"), self.state)