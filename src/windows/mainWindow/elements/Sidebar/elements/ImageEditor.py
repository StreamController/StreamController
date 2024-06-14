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

from src.backend.DeckManagement.InputIdentifier import Input, InputIdentifier
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

    def load_for_identifier(self, identifier: InputIdentifier, state: int):
        self.image_group.load_for_identifier(identifier, state)


class ImageGroup(Adw.PreferencesGroup):
    def __init__(self, sidebar, **kwargs):
        super().__init__(**kwargs)
        self.sidebar = sidebar

        self.build()

    def build(self):
        self.expander = Layout(self)
        self.add(self.expander)

        return

    def load_for_identifier(self, identifier: InputIdentifier, state: int):
        self.expander.load_for_identifier(identifier, state)


class Layout(Adw.ExpanderRow):
    def __init__(self, margin_group):
        super().__init__(title=gl.lm.get("right-area.image-editor.layout.header"), subtitle=gl.lm.get("right-area.image-editor.layout.subtitle"))
        self.margin_group = margin_group
        self.identifier: InputIdentifier = None
        self.active_state: int = None
        self.build()

    def build(self):
        self.size_row = SizeRow(sidebar=self.margin_group.sidebar)
        self.add_row(self.size_row)

        self.valign_row = ValignRow(sidebar=self.margin_group.sidebar)
        self.add_row(self.valign_row)

        self.halign_row = HalignRow(sidebar=self.margin_group.sidebar)
        self.add_row(self.halign_row)

    def load_for_identifier(self, identifier: InputIdentifier, state: int):
        self.active_identifier = identifier
        self.active_state = state

        self.size_row.load_for_identifier(identifier, state)
        self.valign_row.load_for_identifier(identifier, state)
        self.halign_row.load_for_identifier(identifier, state)


class SizeRow(Adw.PreferencesRow):
    def __init__(self, sidebar, **kwargs):
        super().__init__(**kwargs)
        self.sidebar = sidebar
        self.active_identifier: InputIdentifier = None
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

    def load_for_identifier(self, identifier: InputIdentifier, state: int):
        self.disconnect_signals()
        self.active_identifier = identifier
        self.active_state = state

        controller = gl.app.main_win.get_active_controller()
        if controller is None:
            return

        controller_input = controller.get_input(identifier)
        use_page_properties = controller_input.get_active_state().layout_manager.get_use_page_layout_properties()
        self.size_spinner.revert_button.set_visible(use_page_properties.get("size", False))

        self.update_values()

        self.connect_signals()

    def update_values(self, composed_label: KeyLabel = None):
        self.disconnect_signals()
        if composed_label is None:
            visible_child = gl.app.main_win.leftArea.deck_stack.get_visible_child()
            if visible_child is None:
                return
            controller = visible_child.deck_controller
            if controller is None:
                return
            controller_input = controller.get_input(self.active_identifier)
            composed_label = controller_input.get_active_state().layout_manager.get_composed_layout()

        self.size_spinner.button.set_value(composed_label.size*100)

        self.connect_signals()

    def on_size_changed(self, widget):
        active_page = gl.app.main_win.get_active_page()
        active_page.set_media_size(identifier=self.active_identifier, state=self.active_state, size=widget.get_value()/100)

        self.size_spinner.revert_button.set_visible(True)

    def on_size_reset(self, widget):
        active_page = gl.app.main_win.get_active_page()
        active_page.set_media_size(identifier=self.active_identifier, state=self.active_state, size=None)

        self.size_spinner.revert_button.set_visible(False)
        self.update_values()

    def connect_signals(self):
        self.size_spinner.button.connect("value-changed", self.on_size_changed)

    def disconnect_signals(self):
        try:
            self.size_spinner.button.disconnect_by_func(self.on_size_changed)
        except:
            pass


class AlignmentRow(Adw.PreferencesRow):
    def __init__(self, sidebar, label_text, property_name, **kwargs):
        super().__init__(**kwargs)
        self.sidebar = sidebar
        self.property_name = property_name
        self.active_identifier: InputIdentifier = None
        self.active_state: int = None
        self.build(label_text)

        self.connect_signals()

    def build(self, label_text):
        self.main_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, hexpand=True,
                                margin_start=15, margin_end=15, margin_top=15, margin_bottom=15)
        self.set_child(self.main_box)

        self.label = Gtk.Label(label=label_text, hexpand=True, xalign=0)
        self.main_box.append(self.label)

        self.alignment_spinner = SpinButton(-1, 1, 0.1)
        self.main_box.append(self.alignment_spinner)

        self.alignment_spinner.revert_button.connect("clicked", self.on_alignment_reset)

    def load_for_identifier(self, identifier: InputIdentifier, state: int):
        self.active_identifier = identifier
        self.active_state = state
        self.disconnect_signals()

        controller = gl.app.main_win.get_active_controller()

        controller_input = controller.get_input(identifier)
        use_page_properties = controller_input.get_active_state().layout_manager.get_use_page_layout_properties()
        self.alignment_spinner.revert_button.set_visible(use_page_properties.get(self.property_name, False))

        self.connect_signals()
        self.update_values()

    def update_values(self, composed_label: KeyLabel = None):
        self.disconnect_signals()
        if composed_label is None:
            controller = gl.app.main_win.get_active_controller()
            if controller is None:
                return
            controller_input = controller.get_input(self.active_identifier)
            composed_label = controller_input.get_active_state().layout_manager.get_composed_layout()

        self.alignment_spinner.button.set_value(getattr(composed_label, self.property_name))

        self.connect_signals()

    def on_alignment_changed(self, widget):
        active_page = gl.app.main_win.get_active_page()

        page_method = getattr(active_page, f"set_media_{self.property_name}")
        page_method(self.active_identifier, self.active_state, widget.get_value())

        self.alignment_spinner.revert_button.set_visible(True)

    def on_alignment_reset(self, widget):
        active_page = gl.app.main_win.get_active_page()

        page_method = getattr(active_page, f"set_media_{self.property_name}")
        page_method(self.active_identifier, self.active_state, None)

        self.alignment_spinner.revert_button.set_visible(False)
        self.update_values()

    def connect_signals(self):
        self.alignment_spinner.button.connect("value-changed", self.on_alignment_changed)

    def disconnect_signals(self):
        self.alignment_spinner.button.disconnect_by_func(self.on_alignment_changed)

class ValignRow(AlignmentRow):
    def __init__(self, sidebar, **kwargs):
        super().__init__(sidebar, label_text=gl.lm.get("right-area.image-editor.layout.valign.label"), property_name="valign", **kwargs)

class HalignRow(AlignmentRow):
    def __init__(self, sidebar, **kwargs):
        super().__init__(sidebar, label_text=gl.lm.get("right-area.image-editor.layout.halign.label"), property_name="halign", **kwargs)


class SpinButton(Gtk.Box):
    def __init__(self, start: float, end: float, step: float, **kwargs):
        super().__init__(css_classes=["linked"], **kwargs)

        self.button = Gtk.SpinButton.new_with_range(start, end, step)
        self.revert_button = RevertButton()

        self.append(self.button)
        self.append(self.revert_button)