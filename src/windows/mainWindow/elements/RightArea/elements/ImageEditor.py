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
from gi.repository import Gtk, Adw, Gdk, Pango

# Import Python modules
from loguru import logger as log

# Import globals
import globals as gl

# Import own modules
from src.windows.mainWindow.elements.RightArea.elements.IconSelector import IconSelector
from src.backend.PageManagement.Page import Page
from src.backend.DeckManagement.DeckController import DeckController

class ImageEditor(Gtk.Box):
    def __init__(self, right_area, **kwargs):
        self.right_area = right_area
        super().__init__(**kwargs)
        self.build()

    def build(self):
        self.clamp = Adw.Clamp()
        self.append(self.clamp)

        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, hexpand=True)
        self.clamp.set_child(self.main_box)

        self.image_group = ImageGroup(self.right_area)
        self.main_box.append(self.image_group)

    def load_for_coords(self, coords):
        self.image_group.load_for_coords(coords)


class ImageGroup(Adw.PreferencesGroup):
    def __init__(self, right_area, **kwargs):
        super().__init__(**kwargs)
        self.right_area = right_area

        self.build()

    def build(self):
        self.expander = MarginExpanderRow(self)
        self.add(self.expander)

        return

    def load_for_coords(self, coords):
        self.expander.load_for_coords(coords)

class MarginExpanderRow(Adw.ExpanderRow):
    def __init__(self, margin_group):
        super().__init__(title=gl.lm.get("image-editor.header"), subtitle=gl.lm.get("image-editor-expander.subtitle"))
        self.margin_group = margin_group
        self.active_coords = None
        self.build()

    def build(self):
        self.margin_row = MarginRow(right_area=self.margin_group.right_area)
        self.add_row(self.margin_row)

    def load_for_coords(self, coords):
        self.active_coords = coords

        self.margin_row.load_for_coords(coords)

class MarginRow(Adw.PreferencesRow):
    def __init__(self, right_area, **kwargs):
        super().__init__(**kwargs)
        self.right_area = right_area
        self.active_coords = None
        self.build()

    def build(self):
        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, hexpand=True,
                                margin_start=15, margin_end=15, margin_top=15, margin_bottom=15)
        self.set_child(self.main_box)

        self.label = Gtk.Label(label=gl.lm.get("image-editor.margin.label"), hexpand=True, xalign=0, margin_bottom=15)
        self.main_box.append(self.label)

        self.top_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, hexpand=False, halign=Gtk.Align.CENTER)
        self.main_box.append(self.top_box)

        self.top_spinner = Gtk.SpinButton()
        self.top_spinner.set_range(0, 40)
        self.top_spinner.set_increments(1, 5)
        self.top_box.append(self.top_spinner)

        self.center_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, hexpand=False, halign=Gtk.Align.CENTER, homogeneous=False)
        self.main_box.append(self.center_box)

        self.left_spinner = Gtk.SpinButton(orientation=Gtk.Orientation.VERTICAL, vexpand=False, valign=Gtk.Align.CENTER)
        self.left_spinner.set_range(0, 40)
        self.left_spinner.set_increments(1, 5)
        self.center_box.append(self.left_spinner)

        self.icon_selector = IconSelector(self.right_area)
        self.center_box.append(self.icon_selector)

        self.right_spinner = Gtk.SpinButton(orientation=Gtk.Orientation.VERTICAL, vexpand=False, valign=Gtk.Align.CENTER)
        self.right_spinner.set_range(0, 40)
        self.right_spinner.set_increments(1, 5)
        self.center_box.append(self.right_spinner)

        self.bottom_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, hexpand=False, halign=Gtk.Align.CENTER)
        self.main_box.append(self.bottom_box)

        self.bottom_spinner = Gtk.SpinButton()
        self.bottom_spinner.set_range(0, 40)
        self.bottom_spinner.set_increments(1, 5)
        self.bottom_box.append(self.bottom_spinner)

        self.connect_signals()

    def load_for_coords(self, coords):
        self.disconnect_signals()

        self.active_coords = coords
        page = self.get_page()

        x, y = coords

        margins = page.dict.get("keys").get(f"{x}x{y}", {}).get("media", {}).get("margins", [0, 0, 0, 0])

        self.top_spinner.set_value(margins[0])
        self.left_spinner.set_value(margins[1])
        self.right_spinner.set_value(margins[2])
        self.bottom_spinner.set_value(margins[3])

        self.connect_signals()

    def get_deck_controller(self) -> DeckController:
        return self.right_area.main_window.leftArea.deck_stack.get_visible_child().deck_controller

    def get_page(self) -> Page:
        return self.get_deck_controller().active_page

    def connect_signals(self):
        self.top_spinner.connect("value-changed", self.on_margin_changed)
        self.left_spinner.connect("value-changed", self.on_margin_changed)
        self.right_spinner.connect("value-changed", self.on_margin_changed)
        self.bottom_spinner.connect("value-changed", self.on_margin_changed)

    def disconnect_signals(self):
        self.top_spinner.disconnect_by_func(self.on_margin_changed)
        self.left_spinner.disconnect_by_func(self.on_margin_changed)
        self.right_spinner.disconnect_by_func(self.on_margin_changed)
        self.bottom_spinner.disconnect_by_func(self.on_margin_changed)

    def on_margin_changed(self, spinner):
        page = self.get_page()

        page_coords = f"{self.active_coords[0]}x{self.active_coords[1]}"

        page.dict.setdefault("keys", {})
        page.dict["keys"].setdefault(page_coords, {})
        page.dict["keys"][page_coords].setdefault("media", {})
        
        margins = [int(self.left_spinner.get_value()), int(self.top_spinner.get_value()), int(self.right_spinner.get_value()), int(self.bottom_spinner.get_value())]
        page.dict["keys"][page_coords]["media"]["margins"] = margins

        page.save()

        # Reload key
        deck_controller = self.get_deck_controller()
        deck_controller.load_key(key=deck_controller.coords_to_index(self.active_coords), page=deck_controller.active_page)