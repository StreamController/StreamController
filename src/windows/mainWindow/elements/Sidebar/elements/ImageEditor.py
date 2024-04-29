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

from src.backend.DeckManagement.HelperMethods import add_default_keys

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
from src.backend.DeckManagement.DeckController import DeckController, KeyLabel
from GtkHelper.GtkHelper import RevertButton


class ImageEditor(Gtk.Box):
    def __init__(self, sidebar, **kwargs):
        self.sidebar = sidebar
        super().__init__(**kwargs)
        self.build()

    def build(self):
        self.clamp = Adw.Clamp()
        self.append(self.clamp)

        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, hexpand=True)
        self.clamp.set_child(self.main_box)

        self.image_group = ImageGroup(self.sidebar)
        self.main_box.append(self.image_group)

    def load_for_coords(self, coords: tuple[int, int], state: int):
        self.image_group.load_for_coords(coords, state)


class ImageGroup(Adw.PreferencesGroup):
    def __init__(self, sidebar, **kwargs):
        super().__init__(**kwargs)
        self.sidebar = sidebar

        self.build()

    def build(self):
        self.expander = Layout(self)
        self.add(self.expander)

        return

    def load_for_coords(self, coords: tuple[int, int], state: int):
        self.expander.load_for_coords(coords, state)


class Layout(Adw.ExpanderRow):
    def __init__(self, margin_group):
        super().__init__(title=gl.lm.get("right-area.image-editor.layout.header"), subtitle=gl.lm.get("right-area.image-editor.layout.subtitle"))
        self.margin_group = margin_group
        self.active_coords = None
        self.active_state: int = None
        self.build()

    def build(self):
        self.size_row = SizeRow(sidebar=self.margin_group.sidebar)
        self.add_row(self.size_row)

        self.valign_row = ValignRow(sidebar=self.margin_group.sidebar)
        self.add_row(self.valign_row)

        self.halign_row = HalignRow(sidebar=self.margin_group.sidebar)
        self.add_row(self.halign_row)

    def load_for_coords(self, coords: tuple[int, int], state: int):
        self.active_coords = coords
        self.active_state = state

        self.size_row.load_for_coords(coords, state)
        self.valign_row.load_for_coords(coords, state)
        self.halign_row.load_for_coords(coords, state)


class SizeRow(Adw.PreferencesRow):
    def __init__(self, sidebar, **kwargs):
        super().__init__(**kwargs)
        self.sidebar = sidebar
        self.active_coords = None
        self.build()

        self.connect_signals()

    def build(self):
        self.main_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, hexpand=True,
                                margin_start=15, margin_end=15, margin_top=15, margin_bottom=15)
        self.set_child(self.main_box)

        self.label = Gtk.Label(label=gl.lm.get("right-area.image-editor.layout.size.label"), hexpand=True, xalign=0)
        self.main_box.append(self.label)

        self.size_spinner = SpinButton(0, 200, 1)
        self.main_box.append(self.size_spinner)

        self.size_spinner.revert_button.connect("clicked", self.on_size_reset)

    def load_for_coords(self, coords: tuple[int, int], state: int):
        self.disconnect_signals()
        self.active_coords = coords
        self.active_state = state

        visible_child = gl.app.main_win.leftArea.deck_stack.get_visible_child()
        if visible_child is None:
            return
        deck_controller = visible_child.deck_controller
        if deck_controller is None:
            return

        key_index = deck_controller.coords_to_index(self.active_coords)

        use_page_properties = deck_controller.keys[key_index].get_active_state().layout_manager.get_use_page_layout_properties()
        self.size_spinner.revert_button.set_visible(use_page_properties.get("size", False))

        self.update_values()

        self.connect_signals()

    def update_values(self, composed_label: KeyLabel = None):
        self.disconnect_signals()
        if composed_label is None:
            visible_child = gl.app.main_win.leftArea.deck_stack.get_visible_child()
            if visible_child is None:
                return
            deck_controller = visible_child.deck_controller
            if deck_controller is None:
                return
            controller_key = deck_controller.keys[deck_controller.coords_to_index(self.active_coords)]
            composed_label = controller_key.get_active_state().layout_manager.get_composed_layout()

        self.size_spinner.button.set_value(composed_label.size*100)

        self.connect_signals()

    def on_size_changed(self, widget):
        visible_child = gl.app.main_win.leftArea.deck_stack.get_visible_child()
        if visible_child is None:
            return
        deck_controller = visible_child.deck_controller
        if deck_controller is None:
            return

        add_default_keys(deck_controller.active_page.dict, ["keys", f"{self.active_coords[0]}x{self.active_coords[1]}", "states", str(self.state), "media"])
        deck_controller.active_page.dict["keys"][f"{self.active_coords[0]}x{self.active_coords[1]}"]["states"][str(self.state)]["media"]["size"] = widget.get_value() / 100

        deck_controller.active_page.save()

        # Reload key on all decks that have this page loaded
        for deck_controller in gl.deck_manager.deck_controller:
            if deck_controller.active_page.json_path != deck_controller.active_page.json_path:
                continue
            key_index = deck_controller.coords_to_index(self.active_coords)
            if key_index >= len(deck_controller.keys):
                continue
            controller_key = deck_controller.keys[key_index]

            layout = controller_key.layout_manager.page_layout
            layout.size = widget.get_value() / 100
            controller_key.update()

        self.size_spinner.revert_button.set_visible(True)

    def on_size_reset(self, widget):
        visible_child = gl.app.main_win.leftArea.deck_stack.get_visible_child()
        if visible_child is None:
            return
        deck_controller = visible_child.deck_controller
        if deck_controller is None:
            return

        add_default_keys(deck_controller.active_page.dict, ["keys", f"{self.active_coords[0]}x{self.active_coords[1]}", "states", str(self.state), "media"])
        deck_controller.active_page.dict["keys"][f"{self.active_coords[0]}x{self.active_coords[1]}"]["states"][str(self.state)]["media"]["size"] = None

        deck_controller.active_page.save()

        # Reload key on all decks that have this page loaded
        for deck_controller in gl.deck_manager.deck_controller:
            if deck_controller.active_page.json_path != deck_controller.active_page.json_path:
                continue
            key_index = deck_controller.coords_to_index(self.active_coords)
            if key_index >= len(deck_controller.keys):
                continue
            controller_key = deck_controller.keys[key_index]

            layout = controller_key.layout_manager.page_layout
            layout.size = None
            controller_key.update()

        self.size_spinner.revert_button.set_visible(False)
        self.update_values()

    def connect_signals(self):
        self.size_spinner.button.connect("value-changed", self.on_size_changed)

    def disconnect_signals(self):
        try:
            self.size_spinner.button.disconnect_by_func(self.on_size_changed)
        except:
            pass


class ValignRow(Adw.PreferencesRow):
    def __init__(self, sidebar, **kwargs):
        super().__init__(**kwargs)
        self.sidebar = sidebar
        self.active_coords = None
        self.active_state = None
        self.build()

        self.connect_signals()

    def build(self):
        self.main_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, hexpand=True,
                                margin_start=15, margin_end=15, margin_top=15, margin_bottom=15)
        self.set_child(self.main_box)

        self.label = Gtk.Label(label=gl.lm.get("right-area.image-editor.layout.valign.label"), hexpand=True, xalign=0)
        self.main_box.append(self.label)

        self.valign_spinner = SpinButton(-1, 1, 0.1)
        self.main_box.append(self.valign_spinner)

        self.valign_spinner.revert_button.connect("clicked", self.on_valign_reset)

    def load_for_coords(self, coords: tuple[int, int], state: int):
        self.disconnect_signals()
        self.active_coords = coords
        self.active_state = state

        visible_child = gl.app.main_win.leftArea.deck_stack.get_visible_child()
        if visible_child is None:
            return
        deck_controller = visible_child.deck_controller
        if deck_controller is None:
            return

        key_index = deck_controller.coords_to_index(self.active_coords)

        use_page_properties = deck_controller.keys[key_index].get_active_state().layout_manager.get_use_page_layout_properties()
        self.valign_spinner.revert_button.set_visible(use_page_properties.get("valign", False))

        self.connect_signals()
        self.update_values()

    def update_values(self, composed_label: KeyLabel = None):
        self.disconnect_signals()
        if composed_label is None:
            visible_child = gl.app.main_win.leftArea.deck_stack.get_visible_child()
            if visible_child is None:
                return
            deck_controller = visible_child.deck_controller
            if deck_controller is None:
                return
            controller_key = deck_controller.keys[deck_controller.coords_to_index(self.active_coords)]
            composed_label = controller_key.get_active_state().layout_manager.get_composed_layout()

        self.valign_spinner.button.set_value(composed_label.valign)

        self.connect_signals()

    def on_valign_changed(self, widget):
        visible_child = gl.app.main_win.leftArea.deck_stack.get_visible_child()
        if visible_child is None:
            return
        deck_controller = visible_child.deck_controller
        if deck_controller is None:
            return

        add_default_keys(deck_controller.active_page.dict, ["keys", f"{self.active_coords[0]}x{self.active_coords[1]}", "states", str(self.state), "media"])
        deck_controller.active_page.dict["keys"][f"{self.active_coords[0]}x{self.active_coords[1]}"]["states"][str(self.state)]["media"]["valign"] = widget.get_value()

        deck_controller.active_page.save()

        # Reload key on all decks that have this page loaded
        for deck_controller in gl.deck_manager.deck_controller:
            if deck_controller.active_page.json_path != deck_controller.active_page.json_path:
                continue
            key_index = deck_controller.coords_to_index(self.active_coords)
            if key_index >= len(deck_controller.keys):
                continue
            controller_key = deck_controller.keys[key_index]

            layout = controller_key.layout_manager.page_layout
            layout.valign = widget.get_value()
            controller_key.update()

        self.valign_spinner.revert_button.set_visible(True)

    def on_valign_reset(self, widget):
        visible_child = gl.app.main_win.leftArea.deck_stack.get_visible_child()
        if visible_child is None:
            return
        deck_controller = visible_child.deck_controller
        if deck_controller is None:
            return

        add_default_keys(deck_controller.active_page.dict, ["keys", f"{self.active_coords[0]}x{self.active_coords[1]}", "states", str(self.state), "media"])
        deck_controller.active_page.dict["keys"][f"{self.active_coords[0]}x{self.active_coords[1]}"]["states"][str(self.state)]["media"]["valign"] = None

        deck_controller.active_page.save()

        # Reload key on all decks that have this page loaded
        for deck_controller in gl.deck_manager.deck_controller:
            if deck_controller.active_page.json_path != deck_controller.active_page.json_path:
                continue
            key_index = deck_controller.coords_to_index(self.active_coords)
            if key_index >= len(deck_controller.keys):
                continue
            controller_key = deck_controller.keys[key_index]

            layout = controller_key.layout_manager.page_layout
            layout.valign = None
            controller_key.update()

        self.valign_spinner.revert_button.set_visible(False)
        self.update_values()

    def connect_signals(self):
        self.valign_spinner.button.connect("value-changed", self.on_valign_changed)

    def disconnect_signals(self):
        self.valign_spinner.button.disconnect_by_func(self.on_valign_changed)


class HalignRow(Adw.PreferencesRow):
    def __init__(self, sidebar, **kwargs):
        super().__init__(**kwargs)
        self.sidebar = sidebar
        self.active_coords = None
        self.active_state = None
        self.build()

        self.connect_signals()

    def build(self):
        self.main_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, hexpand=True,
                                margin_start=15, margin_end=15, margin_top=15, margin_bottom=15)
        self.set_child(self.main_box)

        self.label = Gtk.Label(label=gl.lm.get("right-area.image-editor.layout.halign.label"), hexpand=True, xalign=0)
        self.main_box.append(self.label)

        self.halign_spinner = SpinButton(-1, 1, 0.1)
        self.main_box.append(self.halign_spinner)

        self.halign_spinner.revert_button.connect("clicked", self.on_halign_reset)

    def load_for_coords(self, coords: tuple[int, int], state: int):
        self.disconnect_signals()
        self.active_coords = coords
        self.active_state = state

        visible_child = gl.app.main_win.leftArea.deck_stack.get_visible_child()
        if visible_child is None:
            return
        deck_controller = visible_child.deck_controller
        if deck_controller is None:
            return

        key_index = deck_controller.coords_to_index(self.active_coords)

        use_page_properties = deck_controller.keys[key_index].get_active_state().layout_manager.get_use_page_layout_properties()
        self.halign_spinner.revert_button.set_visible(use_page_properties.get("halign", False))

        self.connect_signals()
        self.update_values()

    def update_values(self, composed_label: KeyLabel = None):
        self.disconnect_signals()
        if composed_label is None:
            visible_child = gl.app.main_win.leftArea.deck_stack.get_visible_child()
            if visible_child is None:
                return
            deck_controller = visible_child.deck_controller
            if deck_controller is None:
                return
            controller_key = deck_controller.keys[deck_controller.coords_to_index(self.active_coords)]
            composed_label = controller_key.get_active_state().layout_manager.get_composed_layout()

        self.halign_spinner.button.set_value(composed_label.halign)

        self.connect_signals()

    def on_halign_changed(self, widget):
        visible_child = gl.app.main_win.leftArea.deck_stack.get_visible_child()
        if visible_child is None:
            return
        deck_controller = visible_child.deck_controller
        if deck_controller is None:
            return

        add_default_keys(deck_controller.active_page.dict, ["keys", f"{self.active_coords[0]}x{self.active_coords[1]}", "states", str(self.state), "media"])
        deck_controller.active_page.dict["keys"][f"{self.active_coords[0]}x{self.active_coords[1]}"]["states"][str(self.state)]["media"]["halign"] = widget.get_value()

        deck_controller.active_page.save()

        # Reload key on all decks that have this page loaded
        for deck_controller in gl.deck_manager.deck_controller:
            if deck_controller.active_page.json_path != deck_controller.active_page.json_path:
                continue
            key_index = deck_controller.coords_to_index(self.active_coords)
            if key_index >= len(deck_controller.keys):
                continue
            controller_key = deck_controller.keys[key_index]

            layout = controller_key.layout_manager.page_layout
            layout.halign = widget.get_value()
            controller_key.update()

        self.halign_spinner.revert_button.set_visible(True)

    def on_halign_reset(self, widget):
        visible_child = gl.app.main_win.leftArea.deck_stack.get_visible_child()
        if visible_child is None:
            return
        deck_controller = visible_child.deck_controller
        if deck_controller is None:
            return

        add_default_keys(deck_controller.active_page.dict, ["keys", f"{self.active_coords[0]}x{self.active_coords[1]}", "states", str(self.state), "media"])
        deck_controller.active_page.dict["keys"][f"{self.active_coords[0]}x{self.active_coords[1]}"]["states"][str(self.state)]["media"]["halign"] = None

        deck_controller.active_page.save()

        # Reload key on all decks that have this page loaded
        for deck_controller in gl.deck_manager.deck_controller:
            if deck_controller.active_page.json_path != deck_controller.active_page.json_path:
                continue
            key_index = deck_controller.coords_to_index(self.active_coords)
            if key_index >= len(deck_controller.keys):
                continue
            controller_key = deck_controller.keys[key_index]

            layout = controller_key.layout_manager.page_layout
            layout.halign = None
            controller_key.update()

        self.halign_spinner.revert_button.set_visible(False)
        self.update_values()

    def connect_signals(self):
        self.halign_spinner.button.connect("value-changed", self.on_halign_changed)

    def disconnect_signals(self):
        self.halign_spinner.button.disconnect_by_func(self.on_halign_changed)

class SpinButton(Gtk.Box):
    def __init__(self, start: float, end: float, step: float, **kwargs):
        super().__init__(css_classes=["linked"], **kwargs)

        self.button = Gtk.SpinButton.new_with_range(start, end, step)
        self.revert_button = RevertButton()

        self.append(self.button)
        self.append(self.revert_button)