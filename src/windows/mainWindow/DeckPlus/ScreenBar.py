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

from gi.repository import Gtk, Adw, Gdk, GLib, Gio, GdkPixbuf

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from src.windows.mainWindow.elements.PageSettingsPage import PageSettingsPage

class ScreenBar(Gtk.Frame):
    def __init__(self, page_settings_page: "PageSettingsPage", identifier: Input.Touchscreen, **kwargs):
        self.page_settings_page = page_settings_page
        self.deck_controller = page_settings_page.deck_controller
        self.identifier = identifier

        super().__init__(**kwargs)
        self.set_css_classes(["key-button-frame-hidden"])
        self.set_halign(Gtk.Align.CENTER)
        self.set_hexpand(True)
        # self.set_size_request(80, 10)

        self.pixbuf = None

        # self.image = Gtk.Image(css_classes=["key-image", "plus-screenbar"], hexpand=True, vexpand=True)
        # self.image.set_overflow(Gtk.Overflow.HIDDEN)
        # self.image.set_from_file("Assets/800_100.png")

        self.image = ScreenBarImage(self)
        self.image.set_image(Image.new("RGBA", (800, 100), (0, 0, 0, 0)))
        self.set_child(self.image)

        # self.set_child(self.image)
        focus_controller = Gtk.EventControllerFocus()
        self.image.add_controller(focus_controller)
        focus_controller.connect("enter", self.on_focus_in)

        self.click_ctrl = Gtk.GestureClick().new()
        self.click_ctrl.connect("pressed", self.on_click)
        self.click_ctrl.connect("released", self.on_released)
        self.click_ctrl.set_button(0)
        self.image.add_controller(self.click_ctrl)

        # Make image focusable
        self.set_focus_child(self.image)
        self.image.set_focusable(True)

        self.min_drag_distance = 20
        self.long_press_treshold = 0.5

        self.drag_start_xy: tuple[int, int] = None
        self.drag_start_time: float = None

        ## Actions
        self.action_group = Gio.SimpleActionGroup()
        self.insert_action_group("screen", self.action_group)

        self.remove_action = Gio.SimpleAction.new("remove", None)
        self.remove_action.connect("activate", self.on_remove)
        self.action_group.add_action(self.remove_action)

        ## Shortcuts
        self.shortcut_controller = Gtk.ShortcutController()
        self.add_controller(self.shortcut_controller)

        remove_shortcut_action = Gtk.CallbackAction.new(self.on_remove)

        self.remove_shortcut = Gtk.Shortcut.new(Gtk.ShortcutTrigger.parse_string("Delete"), remove_shortcut_action)
        self.shortcut_controller.add_shortcut(self.remove_shortcut)

        self.connect("map", self.on_map)

        self.load_from_changes()

    def on_map(self, widget):
        self.load_from_changes()

    def load_from_changes(self) -> None:
        # Applt changes made before creation of self
        if not hasattr(self.deck_controller, "ui_image_changes_while_hidden"):
            return
        tasks = self.deck_controller.ui_image_changes_while_hidden

        if self.identifier in tasks:
            self.image.set_image(tasks[self.identifier])
            tasks.pop(self.identifier)

    def on_click(self, gesture, n_press, x, y):
        # print(f"Click: {self.parse_xy(x, y)}")
        self.drag_start_xy = None
        self.drag_start_time = None
        if gesture.get_current_button() == 1 and n_press == 1:
            if self.image.has_focus():
                self.drag_start_xy = self.parse_xy(x, y)
                self.drag_start_time = time.time()
            # Single left click
            # Select key
            self.image.grab_focus()

            controller_input = self.page_settings_page.deck_controller.get_input(self.identifier)
            state = controller_input.get_active_state().state
            gl.app.main_win.sidebar.load_for_identifier(self.identifier, state)
            
        elif gesture.get_current_button() == 1 and n_press == 2:
            pass
            # Double left click
            # Simulate key press
            # self.simulate_press()

    def on_released(self, gesture, n_press, x, y):
        if None in [self.drag_start_xy, self.drag_start_time]:
            return
        # print(f"Release: {self.parse_xy(x, y)}")
        x, y = self.parse_xy(x, y)
        start_x, start_y = self.drag_start_xy
        drag_distance = abs(x - start_x) + abs(y - start_y)

        controller = gl.app.main_win.get_active_controller()
        if controller is None:
            return

        if drag_distance > self.min_drag_distance:
            # print(f"Drag from {start_x}, {start_y} to {x}, {y}")
            value = {
                "x": start_x,
                "y": start_y,
                "x_out": x,
                "y_out": y
            }
            # controller.touchscreen_event_callback(controller.deck, TouchscreenEventType.DRAG, value)
            controller.event_callback(self.identifier, TouchscreenEventType.DRAG, value)
            return
        
        if time.time() - self.drag_start_time >= self.long_press_treshold:
            controller.event_callback(self.identifier, TouchscreenEventType.LONG, {"x": x, "y": y})
        
        else:
            controller.event_callback(self.identifier, TouchscreenEventType.SHORT, {"x": x, "y": y})

    def parse_xy(self, x, y) -> tuple[int, int]:
        width = self.image.get_width()
        height = self.image.get_height()

        # Map xy to 800x100
        x, y = int(x * 800 / width), int(y * 100 / height)

        x = max(0, min(x, 800))
        y = max(0, min(y, 100))

        return x, y


    def on_focus_in(self, *args):
        self.set_border_active(True)

    def set_border_active(self, active: bool):
        if active:
            if self.page_settings_page.deck_config.active_widget not in [self, None]:
                self.page_settings_page.deck_config.active_widget.set_border_active(False)
            self.page_settings_page.deck_config.active_widget = self
            self.set_css_classes(["key-button-frame"])
        else:
            self.set_css_classes(["key-button-frame-hidden"])
            self.page_settings_page.deck_config.active_widget = None

    def on_remove(self, *args) -> None:
        controller = gl.app.main_win.get_active_controller()
        if controller is None:
            return
        
        active_page = controller.active_page
        if active_page is None:
            return

        screen = controller.get_input(self.identifier)
        
        if str(screen.state) not in active_page.dict.get(self.identifier.input_type, {}).get(self.identifier.json_identifier, {}).get("states", {}):
            return
        
        del active_page.dict[self.identifier.input_type][self.identifier.json_identifier]["states"][str(screen.state)]
        active_page.save()
        active_page.load()

        active_page.reload_similar_pages(identifier=self.identifier, reload_self=True)

        # Reload ui
        gl.app.main_win.sidebar.load_for_identifier(self.identifier, screen.state)

class ScreenBarImage(Gtk.Picture):
    PREVIEW_MAX_WIDTH = 385
    PREVIEW_MAX_HEIGHT = 49

    def __init__(self, screenbar: ScreenBar, **kwargs):
        super().__init__(keep_aspect_ratio=True, can_shrink=True, content_fit=Gtk.ContentFit.SCALE_DOWN,
                         halign=Gtk.Align.CENTER, hexpand=False, width_request=80, height_request=10,
                         valign=Gtk.Align.CENTER, vexpand=False, css_classes=["plus-screenbar-image"],
                         **kwargs)
        
        self.screenbar = screenbar
        self.full_image: Image.Image = None
        self.thumbnail_image: Image.Image = None
        self.thumbnail_pixbuf: GdkPixbuf.Pixbuf = None

        self.on_map_tasks: list[callable] = []
        self.connect("map", self.on_map)

        self.latest_task_id: int = None


        # screen_image = self.get_controller_touch_screen().get_current_image()
        # self.set_image(screen_image)

    def on_map(self, *args):
        for task in self.on_map_tasks:
            task()
        self.on_map_tasks.clear()
        
    def get_controller_touch_screen(self) -> "ControllerTouchScreen":
        controller = gl.app.main_win.get_active_controller()
        return controller.get_input(Input.Touchscreen("sd-plus"))
    
    def get_controller_dial(self, identifier: InputIdentifier) -> "ControllerDial":
        controller = gl.app.main_win.get_active_controller()
        return controller.get_input(identifier)
    
    def get_new_task_id(self):
        if self.latest_task_id is None:
            return 0

        return self.latest_task_id + 1
        
    def set_image(self, image: Image.Image):
        if not self.get_mapped():
            self.on_map_tasks = [lambda image=image: self.set_image(image)]
            return

        if self.full_image is not None:
            self.full_image.close()
        self.full_image = image
        self._rebuild_thumbnail()

        self.refresh_preview()

    def update_region(self, region: Image.Image, x_pos: int, y_pos: int, identifier: InputIdentifier = None):
        if not self.get_mapped():
            region.close()
            return False

        if self.full_image is None:
            region.close()
            return False

        self.full_image.paste(region, (x_pos, y_pos))
        self._update_thumbnail_region(region, x_pos, y_pos)

        dial_preview = None
        if recursive_hasattr(gl, "app.main_win.sidebar") and gl.app.main_win.sidebar.active_identifier == identifier:
            dial_preview = region.copy()

        region.close()
        self.refresh_preview(dial_preview=dial_preview)
        return False

    def _get_preview_size(self) -> tuple[int, int]:
        if self.full_image is None:
            return self.PREVIEW_MAX_WIDTH, self.PREVIEW_MAX_HEIGHT

        width, height = self.full_image.size
        scale = min(self.PREVIEW_MAX_WIDTH / width, self.PREVIEW_MAX_HEIGHT / height)
        preview_width = max(1, int(width * scale))
        preview_height = max(1, int(height * scale))
        return preview_width, preview_height

    def _rebuild_thumbnail(self) -> None:
        if self.thumbnail_image is not None:
            self.thumbnail_image.close()
        preview_size = self._get_preview_size()
        self.thumbnail_image = self.full_image.resize(preview_size, Image.Resampling.LANCZOS)
        self._rebuild_thumbnail_pixbuf()

    def _rebuild_thumbnail_pixbuf(self) -> None:
        source_pixbuf = image2pixbuf(self.thumbnail_image, force_transparency=True)
        self.thumbnail_pixbuf = GdkPixbuf.Pixbuf.new(
            GdkPixbuf.Colorspace.RGB,
            True,
            8,
            source_pixbuf.get_width(),
            source_pixbuf.get_height(),
        )
        source_pixbuf.copy_area(
            0,
            0,
            source_pixbuf.get_width(),
            source_pixbuf.get_height(),
            self.thumbnail_pixbuf,
            0,
            0,
        )

    def _update_thumbnail_region(self, region: Image.Image, x_pos: int, y_pos: int) -> None:
        if self.thumbnail_image is None or self.thumbnail_pixbuf is None:
            self._rebuild_thumbnail()
            return

        full_width, full_height = self.full_image.size
        thumb_width, thumb_height = self.thumbnail_image.size

        x2 = x_pos + region.width
        y2 = y_pos + region.height

        thumb_x1 = int(x_pos * thumb_width / full_width)
        thumb_y1 = int(y_pos * thumb_height / full_height)
        thumb_x2 = max(thumb_x1 + 1, int((x2 * thumb_width + full_width - 1) / full_width))
        thumb_y2 = max(thumb_y1 + 1, int((y2 * thumb_height + full_height - 1) / full_height))

        resized_region = region.resize((thumb_x2 - thumb_x1, thumb_y2 - thumb_y1), Image.Resampling.LANCZOS)
        self.thumbnail_image.paste(resized_region, (thumb_x1, thumb_y1))
        region_pixbuf = image2pixbuf(resized_region, force_transparency=True)
        region_pixbuf.copy_area(
            0,
            0,
            region_pixbuf.get_width(),
            region_pixbuf.get_height(),
            self.thumbnail_pixbuf,
            thumb_x1,
            thumb_y1,
        )
        resized_region.close()

    def refresh_preview(self, dial_preview: Image.Image = None):
        self.latest_task_id = self.get_new_task_id()
        GLib.idle_add(self.set_cached_pixbuf, self.latest_task_id, priority=GLib.PRIORITY_HIGH)

        if not recursive_hasattr(gl, "app.main_win.sidebar"):
            if dial_preview is not None:
                dial_preview.close()
            return

        identifier = gl.app.main_win.sidebar.active_identifier
        if isinstance(identifier, Input.Dial):
            if dial_preview is None:
                dial_image_area = self.get_controller_touch_screen().get_dial_image_area(identifier)
                dial_preview = self.full_image.crop(dial_image_area)

            GLib.idle_add(gl.app.main_win.sidebar.key_editor.icon_selector.set_image, dial_preview)

    def set_cached_pixbuf(self, task_id: int = None):
        if task_id is not None:
            if task_id != self.latest_task_id:
                log.debug("Screenbar: Abort task")
                return False
        self.set_pixbuf(self.thumbnail_pixbuf)
        return False
