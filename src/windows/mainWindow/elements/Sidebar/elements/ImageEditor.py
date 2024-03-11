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
from src.windows.mainWindow.elements.Sidebar.elements.IconSelector import IconSelector
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
        self.expander = Layout(self)
        self.add(self.expander)

        return

    def load_for_coords(self, coords):
        self.expander.load_for_coords(coords)


class Layout(Adw.ExpanderRow):
    def __init__(self, margin_group):
        super().__init__(title=gl.lm.get("right-area.image-editor.layout.header"), subtitle=gl.lm.get("right-area.image-editor.layout.subtitle"))
        self.margin_group = margin_group
        self.active_coords = None
        self.build()

    def build(self):
        self.size_row = SizeRow(right_area=self.margin_group.right_area)
        self.add_row(self.size_row)

        self.valign_row = ValignRow(right_area=self.margin_group.right_area)
        self.add_row(self.valign_row)

        self.halign_row = HalignRow(right_area=self.margin_group.right_area)
        self.add_row(self.halign_row)

    def load_for_coords(self, coords):
        self.active_coords = coords

        self.size_row.load_for_coords(coords)
        self.valign_row.load_for_coords(coords)
        self.halign_row.load_for_coords(coords)


class SizeRow(Adw.PreferencesRow):
    def __init__(self, right_area, **kwargs):
        super().__init__(**kwargs)
        self.right_area = right_area
        self.active_coords = None
        self.build()

        self.connect_signals()

    def build(self):
        self.main_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, hexpand=True,
                                margin_start=15, margin_end=15, margin_top=15, margin_bottom=15)
        self.set_child(self.main_box)

        self.label = Gtk.Label(label=gl.lm.get("right-area.image-editor.layout.size.label"), hexpand=True, xalign=0)
        self.main_box.append(self.label)

        self.size_spinner = Gtk.SpinButton.new_with_range(0, 100, 1)
        self.main_box.append(self.size_spinner)

    def load_for_coords(self, coords):
        self.disconnect_signals()
        self.active_coords = coords

        deck_controller = self.right_area.main_window.leftArea.deck_stack.get_visible_child().deck_controller

        self.size_spinner.set_value(deck_controller.active_page.dict.get("keys").get(f"{coords[0]}x{coords[1]}", {}).get("media", {}).get("size", 1) * 100)

        self.connect_signals()

    def on_size_changed(self, widget):
        deck_controller = self.right_area.main_window.leftArea.deck_stack.get_visible_child().deck_controller

        deck_controller.active_page.dict.setdefault("keys", {})
        deck_controller.active_page.dict["keys"].setdefault(f"{self.active_coords[0]}x{self.active_coords[1]}", {})
        deck_controller.active_page.dict["keys"][f"{self.active_coords[0]}x{self.active_coords[1]}"].setdefault("media", {})

        deck_controller.active_page.dict["keys"][f"{self.active_coords[0]}x{self.active_coords[1]}"]["media"]["size"] = widget.get_value() / 100

        deck_controller.active_page.save()

        # Reload key
        deck_controller.load_key(key=deck_controller.coords_to_index(self.active_coords), page=deck_controller.active_page)

    def connect_signals(self):
        self.size_spinner.connect("value-changed", self.on_size_changed)

    def disconnect_signals(self):
        self.size_spinner.disconnect_by_func(self.on_size_changed)


class ValignRow(Adw.PreferencesRow):
    def __init__(self, right_area, **kwargs):
        super().__init__(**kwargs)
        self.right_area = right_area
        self.active_coords = None
        self.build()

        self.connect_signals()

    def build(self):
        self.main_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, hexpand=True,
                                margin_start=15, margin_end=15, margin_top=15, margin_bottom=15)
        self.set_child(self.main_box)

        self.label = Gtk.Label(label=gl.lm.get("right-area.image-editor.layout.valign.label"), hexpand=True, xalign=0)
        self.main_box.append(self.label)

        self.valign_spinner = Gtk.SpinButton.new_with_range(-1, 1, 0.1)
        self.main_box.append(self.valign_spinner)

    def load_for_coords(self, coords):
        self.disconnect_signals()
        self.active_coords = coords

        deck_controller = self.right_area.main_window.leftArea.deck_stack.get_visible_child().deck_controller

        self.valign_spinner.set_value(deck_controller.active_page.dict.get("keys").get(f"{coords[0]}x{coords[1]}", {}).get("media", {}).get("valign", 0))

        self.connect_signals()

    def on_valign_changed(self, widget):
        deck_controller = self.right_area.main_window.leftArea.deck_stack.get_visible_child().deck_controller

        deck_controller.active_page.dict.setdefault("keys", {})
        deck_controller.active_page.dict["keys"].setdefault(f"{self.active_coords[0]}x{self.active_coords[1]}", {})
        deck_controller.active_page.dict["keys"][f"{self.active_coords[0]}x{self.active_coords[1]}"].setdefault("media", {})

        deck_controller.active_page.dict["keys"][f"{self.active_coords[0]}x{self.active_coords[1]}"]["media"]["valign"] = widget.get_value()

        deck_controller.active_page.save()

        # Reload key
        deck_controller.load_key(key=deck_controller.coords_to_index(self.active_coords), page=deck_controller.active_page)

    def connect_signals(self):
        self.valign_spinner.connect("value-changed", self.on_valign_changed)

    def disconnect_signals(self):
        self.valign_spinner.disconnect_by_func(self.on_valign_changed)


class HalignRow(Adw.PreferencesRow):
    def __init__(self, right_area, **kwargs):
        super().__init__(**kwargs)
        self.right_area = right_area
        self.active_coords = None
        self.build()

        self.connect_signals()

    def build(self):
        self.main_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, hexpand=True,
                                margin_start=15, margin_end=15, margin_top=15, margin_bottom=15)
        self.set_child(self.main_box)

        self.label = Gtk.Label(label=gl.lm.get("right-area.image-editor.layout.halign.label"), hexpand=True, xalign=0)
        self.main_box.append(self.label)

        self.halign_spinner = Gtk.SpinButton.new_with_range(-1, 1, 0.1)
        self.main_box.append(self.halign_spinner)

    def load_for_coords(self, coords):
        self.disconnect_signals()
        
        self.active_coords = coords

        deck_controller = self.right_area.main_window.leftArea.deck_stack.get_visible_child().deck_controller

        self.halign_spinner.set_value(deck_controller.active_page.dict.get("keys").get(f"{coords[0]}x{coords[1]}", {}).get("media", {}).get("halign", 0))

        self.connect_signals()

    def on_halign_changed(self, widget):
        deck_controller = self.right_area.main_window.leftArea.deck_stack.get_visible_child().deck_controller

        deck_controller.active_page.dict.setdefault("keys", {})
        deck_controller.active_page.dict["keys"].setdefault(f"{self.active_coords[0]}x{self.active_coords[1]}", {})
        deck_controller.active_page.dict["keys"][f"{self.active_coords[0]}x{self.active_coords[1]}"].setdefault("media", {})

        deck_controller.active_page.dict["keys"][f"{self.active_coords[0]}x{self.active_coords[1]}"]["media"]["halign"] = widget.get_value()

        deck_controller.active_page.save()

        # Reload key
        deck_controller.load_key(key=deck_controller.coords_to_index(self.active_coords), page=deck_controller.active_page)

    def connect_signals(self):
        self.halign_spinner.connect("value-changed", self.on_halign_changed)

    def disconnect_signals(self):
        self.halign_spinner.disconnect_by_func(self.on_halign_changed)