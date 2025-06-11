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
import threading
import time
import gi
from loguru import logger as log

from PIL import Image

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from src.backend.DeckManagement.DeckController import ControllerDial, ControllerTouchScreen
from src.backend.DeckManagement.InputIdentifier import Input, InputIdentifier
from src.backend.DeckManagement.ImageHelpers import image2pixbuf
from src.backend.DeckManagement.HelperMethods import recursive_hasattr

from StreamDeck.Devices.StreamDeck import DialEventType, TouchscreenEventType

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

import globals as gl

from gi.repository import Gtk, Adw, Gdk, GLib, Gio

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from src.windows.mainWindow.elements.PageSettingsPage import PageSettingsPage

class ScreenBar(Gtk.Frame):
    def __init__(self, page_settings_page: "PageSettingsPage", identifier: Input.Screen, **kwargs):
        self.page_settings_page = page_settings_page
        self.deck_controller = page_settings_page.deck_controller
        self.identifier = identifier

        super().__init__(**kwargs)
        self.set_css_classes(["key-button-frame-hidden"])
        self.set_halign(Gtk.Align.CENTER)
        self.set_hexpand(True)

        self.pixbuf = None

        self.image = ScreenBarImage(self)
        size = self.page_settings_page.deck_controller.deck.screen_image_format()["size"]
        self.image.set_image(Image.new("RGBA", size, (0, 0, 0, 0)))
        self.set_child(self.image)

        focus_controller = Gtk.EventControllerFocus()
        self.add_controller(focus_controller)
        focus_controller.connect("enter", self.on_focus_in)

        # Click ctrl
        self.right_click_ctrl = Gtk.GestureClick().new()
        self.right_click_ctrl.connect("pressed", self.on_click)
        self.right_click_ctrl.set_button(0)
        self.image.add_controller(self.right_click_ctrl)

        self.set_focus_child(self.image)
        self.image.set_focusable(True)

    def on_click(self, gesture, n_press, x, y):
        if gesture.get_current_button() == 1 and n_press == 1:
            # Single left click
            # Select key
            self.image.grab_focus()

    def on_focus_in(self, *args):
        # Update settings on the righthand side of the screen
        self.update_sidebar()
        # Update preview
        if self.pixbuf is not None:
            self.set_icon_selector_previews(self.pixbuf)
        self.set_border_active(True)

    def update_sidebar(self):
        if not recursive_hasattr(gl, "app.main_win.sidebar"):
            return
        sidebar = gl.app.main_win.sidebar
        # Check if already loaded for this coords
        if sidebar.active_identifier == self.identifier:
            if not self.get_mapped():
                return

        sidebar.load_for_identifier(self.identifier, None)

    def set_border_active(self, active: bool):
        if active:
            if self.page_settings_page.deck_config.active_widget not in [self, None]:
                self.page_settings_page.deck_config.active_widget.set_border_active(False)
            self.page_settings_page.deck_config.active_widget = self
            self.set_css_classes(["key-button-frame"])
        else:
            self.set_css_classes(["key-button-frame-hidden"])
            self.page_settings_page.deck_config.active_widget = None

class ScreenBarImage(Gtk.Picture):
    def __init__(self, screenbar: ScreenBar, **kwargs):
        super().__init__(keep_aspect_ratio=True, can_shrink=True, content_fit=Gtk.ContentFit.SCALE_DOWN,
                         halign=Gtk.Align.CENTER, hexpand=False, width_request=80, height_request=10,
                         valign=Gtk.Align.CENTER, vexpand=False, css_classes=["plus-screenbar-image"],
                         **kwargs)

        self.screenbar = screenbar

        self.on_map_tasks: list[callable] = []
        self.connect("map", self.on_map)

        self.latest_task_id: int = None

        #screen_image = self.get_controller_screen().get_current_image()
        #self.set_image(screen_image)

    def on_map(self, *args):
        for task in self.on_map_tasks:
            task()
        self.on_map_tasks.clear()

    def get_controller_screen(self) -> "ControllerScreen":
        controller =   gl.app.main_win.get_active_controller()
        return controller.get_input(Input.Screen("sd-neo"))

    def get_new_task_id(self):
        if self.latest_task_id is None:
            return 0

        return self.latest_task_id + 1

    def set_image(self, image: Image.Image):
        if not self.get_mapped():
            self.on_map_tasks = [lambda: self.set_image(image)]
            return

        width = 385 #TODO: Find a better way to do this
        thumbnail = image.copy()
        thumbnail.thumbnail((width, width/8))

        pixbuf = image2pixbuf(thumbnail.convert("RGBA"), force_transparency=True)
        self.latest_task_id = self.get_new_task_id()
        GLib.idle_add(self.set_pixbuf_and_del, pixbuf, self.latest_task_id, priority=GLib.PRIORITY_HIGH)

        thumbnail.close()
        del thumbnail

        if not recursive_hasattr(gl, "app.main_win.sidebar"):
            return

        identifier = gl.app.main_win.sidebar.active_identifier

    def set_pixbuf_and_del(self, pixbuf, task_id: int = None):
        if task_id is not None:
            if task_id != self.latest_task_id:
                log.debug("Screenbar: Abort task")
                return
        self.set_pixbuf(pixbuf)
        del pixbuf
