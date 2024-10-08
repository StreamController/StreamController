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
import threading
import gi

from src.backend.DeckManagement.HelperMethods import color_values_to_gdk, gdk_color_to_values, get_pango_font_description, get_values_from_pango_font_description
from src.backend.DeckManagement.InputIdentifier import InputIdentifier

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, Gdk, Pango, GLib

# Import Python modules
from loguru import logger as log

# Import own modules
from src.backend.DeckManagement.DeckController import KeyLabel
from GtkHelper.GtkHelper import RevertButton

# Import globals
import globals as gl

class LabelEditor(Gtk.Box):
    def __init__(self, sidebar, **kwargs):
        self.sidebar = sidebar
        super().__init__(**kwargs)
        self.build()

    def build(self):
        self.clamp = Adw.Clamp()
        self.append(self.clamp)

        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, hexpand=True)
        self.clamp.set_child(self.main_box)

        self.label_group = LabelGroup(self.sidebar)
        self.main_box.append(self.label_group)

    def load_for_identifier(self, identifier: InputIdentifier, state: int):
        self.label_group.load_for_identifier(identifier, state)


class LabelGroup(Adw.PreferencesGroup):
    def __init__(self, sidebar, **kwargs):
        super().__init__(**kwargs)
        self.sidebar = sidebar

        self.build()

    def build(self):
        self.expander = LabelExpanderRow(self)
        self.add(self.expander)

        return

    def load_for_identifier(self, identifier: InputIdentifier, state: int):
        self.expander.load_for_identifier(identifier, state)

class LabelExpanderRow(Adw.ExpanderRow):
    def __init__(self, label_group):
        super().__init__(title=gl.lm.get("label-editor-header"), subtitle=gl.lm.get("label-editor-expander-subtitle"))
        self.label_group = label_group
        self.active_identifier: InputIdentifier = None
        self.build()

    def build(self):
        self.top_row = LabelRow(gl.lm.get("label-editor-top-name"), 0, self.label_group.sidebar, key_name="top")
        self.center_row = LabelRow(gl.lm.get("label-editor-center-name"), 1, self.label_group.sidebar, key_name="center")
        self.bottom_row = LabelRow(gl.lm.get("label-editor-bottom-name"), 2, self.label_group.sidebar, key_name="bottom")

        self.add_row(self.top_row)
        self.add_row(self.center_row)
        self.add_row(self.bottom_row)

    def load_for_identifier(self, identifier: InputIdentifier, state: int):
        if not isinstance(identifier, InputIdentifier):
            raise TypeError
        self.active_identifier = identifier

        self.top_row.load_for_identifier(identifier, state)
        self.center_row.load_for_identifier(identifier, state)
        self.bottom_row.load_for_identifier(identifier, state)

class LabelRow(Adw.PreferencesRow):
    def __init__(self, label_text, label_index: int, sidebar, key_name: str, **kwargs):
        super().__init__(**kwargs)
        self.label_text = label_text
        self.sidebar = sidebar
        self.active_identifier: InputIdentifier = None
        self.state: int = 0
        self.label_index = label_index
        self.key_name = key_name
        self.build()

        self.lock = threading.Lock()

        self.block = False

        # Connect set signals
        self.connect_signals()

    def build(self):
        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, hexpand=True,
                                margin_start=15, margin_end=15, margin_top=15, margin_bottom=15)
        self.set_child(self.main_box)

        self.label = Gtk.Label(label=self.label_text, xalign=0, margin_bottom=3, css_classes=["bold"])
        self.main_box.append(self.label)

        self.controlled_by_action_label = Gtk.Label(label=gl.lm.get("label-editor-warning-controlled-by-action"), css_classes=["bold", "red-color"], xalign=0,
                                                    margin_bottom=3, visible=False)
        self.main_box.append(self.controlled_by_action_label)

        self.text_view = TextView(placeholder=gl.lm.get("label-editor-placeholder-text"))
        # self.text_view.entry.connect("changed", self.on_change_text)
        self.main_box.append(self.text_view)

        self.color_chooser_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, hexpand=True, margin_top=6)
        self.main_box.append(self.color_chooser_box)

        self.color_chooser_label = Gtk.Label(label=gl.lm.get("label-editor-color-chooser-label"), xalign=0, hexpand=True, margin_start=2)
        self.color_chooser_box.append(self.color_chooser_label)

        self.color_chooser_button = ColorChooserButton()
        # self.color_chooser_button.button.connect("color-set", self.on_change_color)
        self.color_chooser_box.append(self.color_chooser_button)

        self.font_chooser_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, hexpand=True, margin_top=6)
        self.main_box.append(self.font_chooser_box)

        self.font_chooser_label = Gtk.Label(label=gl.lm.get("label-editor-font-chooser-label"), xalign=0, hexpand=True, margin_start=2)
        self.font_chooser_box.append(self.font_chooser_label)

        self.font_chooser_button = FontChooserButton()
        self.font_chooser_box.append(self.font_chooser_button)

        self.outline_width_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, hexpand=True, margin_top=6)
        self.main_box.append(self.outline_width_box)

        self.outline_width_label = Gtk.Label(label=gl.lm.get("label-editor-outline-width-label"), xalign=0, hexpand=True, margin_start=2)
        self.outline_width_box.append(self.outline_width_label)

        self.outline_width = SpinButton(0, 10, 1)
        self.outline_width_box.append(self.outline_width)

        self.outline_color_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, hexpand=True, margin_top=6)
        self.main_box.append(self.outline_color_box)

        self.outline_color_label = Gtk.Label(label=gl.lm.get("label-editor-outline-color-label"), xalign=0, hexpand=True, margin_start=2)
        self.outline_color_box.append(self.outline_color_label)

        self.outline_color_chooser_button = ColorChooserButton()
        self.outline_color_box.append(self.outline_color_chooser_button)

        ## Connect reset buttons
        self.text_view.revert_button.connect("clicked", self.on_reset_text)
        self.color_chooser_button.revert_button.connect("clicked", self.on_reset_color)
        self.font_chooser_button.revert_button.connect("clicked", self.on_reset_font)
        self.outline_width.revert_button.connect("clicked", self.on_reset_outline_width)
        self.outline_color_chooser_button.revert_button.connect("clicked", self.on_reset_outline_color)

    def connect_signals(self):
        self.text_view.entry.get_buffer().connect("changed", self.on_change_text)
        self.color_chooser_button.button.connect("color-set", self.on_change_color)
        self.font_chooser_button.button.connect("font-set", self.on_change_font)
        self.outline_width.button.connect("value-changed", self.on_change_outline_width)
        self.outline_color_chooser_button.button.connect("color-set", self.on_change_outline_color)

    def disconnect_signals(self):
        try:
            self.text_view.entry.get_buffer().disconnect_by_func(self.on_change_text)
        except Exception as e:
            log.error(f"Failed to disconnect signals. Error: {e}")

        try:
            self.color_chooser_button.button.disconnect_by_func(self.on_change_color)
        except Exception as e:
            log.error(f"Failed to disconnect signals. Error: {e}")

        try:
            self.font_chooser_button.button.disconnect_by_func(self.on_change_font)
        except Exception as e:
            log.error(f"Failed to disconnect signals. Error: {e}")

        try:
            self.outline_width.button.disconnect_by_func(self.on_change_outline_width)
        except Exception as e:
            log.error(f"Failed to disconnect signals. Error: {e}")

        try:
            self.outline_color_chooser_button.button.disconnect_by_func(self.on_change_outline_color)
        except Exception as e:
            log.error(f"Failed to disconnect signals. Error: {e}")

    def load_for_identifier(self, identifier: InputIdentifier, state: int):
        if not isinstance(identifier, InputIdentifier):
            raise ValueError
        self.active_identifier = identifier
        self.state = state

        controller = gl.app.main_win.get_active_controller()
        if controller is None:
            return
        page = controller.active_page

        if page == None:
            #TODO: Show error
            return
        
        controller_input = controller.get_input(identifier)
        use_page_label_properties = controller_input.get_active_state().label_manager.get_use_page_label_properties(position=self.key_name)

        ## Set visibility of revert buttons
        self.text_view.set_revert_visible(use_page_label_properties.get("text", False))
        self.color_chooser_button.revert_button.set_visible(use_page_label_properties.get("color", False))
        self.outline_width.revert_button.set_visible(use_page_label_properties.get("outline_width", False))
        self.outline_color_chooser_button.revert_button.set_visible(use_page_label_properties.get("outline_color", False))

        font_combined = use_page_label_properties.get("font-family", False) and use_page_label_properties.get("font-size", False)
        self.font_chooser_button.revert_button.set_visible(font_combined)

        # Set properties
        self.update_values()

    def update_values(self, composed_label: KeyLabel = None):
        self.lock.acquire()
        self.disconnect_signals()
        if composed_label is None:
            controller = gl.app.main_win.get_active_controller()
            controller_input = controller.get_input(self.active_identifier)
            composed_label = controller_input.get_active_state().label_manager.get_composed_label(position=self.key_name)

        buffer = self.text_view.entry.get_buffer()
        start, end = buffer.get_bounds()

        if buffer.get_text(start, end, False) != composed_label.text:
            cursor_iter = buffer.get_iter_at_mark(buffer.get_insert())
            pos = cursor_iter.get_offset()

            if composed_label.text == "":
                self.text_view.entry.get_buffer().set_text(" ")
            
            self.text_view.entry.get_buffer().set_text(composed_label.text)

            pos = min(pos, len(composed_label.text))

            iter = buffer.get_iter_at_offset(pos)
            buffer.place_cursor(iter)

        self.update_details_visibility(text=composed_label.text)

        self.set_color(composed_label.color)
        self.set_outline_width(composed_label.outline_width)
        self.set_outline_color(composed_label.outline_color)

        # self.font_chooser_button.button.set_font_desc(Pango.FontDescription.from_string(f"{composed_label.font_name} {composed_label.style} {composed_label.font_size}px"))
        desc = get_pango_font_description(
            font_family=composed_label.font_name,
            font_size=composed_label.font_size,
            font_style=composed_label.style,
            font_weight=composed_label.font_weight
        )
        self.font_chooser_button.button.set_font_desc(desc)

        self.connect_signals()

        self.lock.release()

    def set_color(self, color_values: list):
        color = color_values_to_gdk(color_values)
        self.color_chooser_button.button.set_rgba(color)

    def set_outline_width(self, outline_width: int):
        self.outline_width.button.set_value(outline_width)

    def set_outline_color(self, color_values: list):
        color = color_values_to_gdk(color_values)
        self.outline_color_chooser_button.button.set_rgba(color)

    def on_change_color(self, _):
        color = self.color_chooser_button.button.get_rgba()
        color = gdk_color_to_values(color)

        active_page = gl.app.main_win.get_active_page()
        active_page.set_label_font_color(identifier=self.active_identifier, state=self.state, label_position=self.key_name, font_color=color)

        self.color_chooser_button.revert_button.set_visible(True)

    def on_change_outline_width(self, _):
        width = int(self.outline_width.button.get_value())

        active_page = gl.app.main_win.get_active_page()
        active_page.set_label_outline_width(identifier=self.active_identifier, state=self.state, label_position=self.key_name, outline_width=width)

        self.outline_width.revert_button.set_visible(True)

    def on_change_outline_color(self, _):
        color = self.outline_color_chooser_button.button.get_rgba()
        color = gdk_color_to_values(color)

        active_page = gl.app.main_win.get_active_page()
        active_page.set_label_outline_color(identifier=self.active_identifier, state=self.state, label_position=self.key_name, outline_color=color)

        self.outline_color_chooser_button.revert_button.set_visible(True)

    def on_change_font(self, button):
        # font = self.font_chooser_button.button.get_font()
        # name, size = self.parse_font_description(font)

        font_desc = self.font_chooser_button.button.get_font_desc()
        name, size, weight, style = get_values_from_pango_font_description(font_desc)

        active_page = gl.app.main_win.get_active_page()
        active_page.set_label_font_family(identifier=self.active_identifier, state=self.state, label_position=self.key_name, font_family=name, update=False)
        active_page.set_label_font_style(identifier=self.active_identifier, state=self.state, label_position=self.key_name, font_style=style, update=False)
        active_page.set_label_font_size(identifier=self.active_identifier, state=self.state, label_position=self.key_name, font_size=size, update=False)
        active_page.set_label_font_weight(identifier=self.active_identifier, state=self.state, label_position=self.key_name, font_weight=weight, update=True)

        self.font_chooser_button.revert_button.set_visible(True)

    def on_reset_font(self, button):
        #FIXME: gets called multiple times
        active_page = gl.app.main_win.get_active_page()
        #TODO
        active_page.set_label_font_family(identifier=self.active_identifier, state=self.state, label_position=self.key_name, font_family=None, update=False)
        active_page.set_label_font_size(identifier=self.active_identifier, state=self.state, label_position=self.key_name, font_size=None, update=True)

        button.set_visible(False)

    def on_reset_text(self, button):
        active_page = gl.app.main_win.get_active_page()
        active_page.set_label_text(identifier=self.active_identifier, state=self.state, label_position=self.key_name, text=None)

        self.update_values()

        self.text_view.set_revert_visible(False)

    def on_reset_color(self, button):
        active_page = gl.app.main_win.get_active_page()
        active_page.set_label_font_color(identifier=self.active_identifier, state=self.state, label_position=self.key_name, font_color=None)

        button.set_visible(False)

    def on_reset_outline_width(self, button):
        active_page = gl.app.main_win.get_active_page()
        active_page.set_label_outline_width(identifier=self.active_identifier, state=self.state, label_position=self.key_name, outline_width=None)

        button.set_visible(False)

    def on_reset_outline_color(self, button):
        active_page = gl.app.main_win.get_active_page()
        active_page.set_label_outline_color(identifier=self.active_identifier, state=self.state, label_position=self.key_name, outline_color=None)

        button.set_visible(False)

    def on_change_text(self, buffer):
        start, end = buffer.get_bounds()
        text = buffer.get_text(start, end, False)

        active_page = gl.app.main_win.get_active_page()
        active_page.set_label_text(identifier=self.active_identifier, state=self.state, label_position=self.key_name, text=text)

        self.text_view.set_revert_visible(True)

        self.update_details_visibility(text=text)

    def update_details_visibility(self, text: str = ""):
        hide_details = text.strip() == ""
        self.color_chooser_box.set_visible(not hide_details)
        self.font_chooser_box.set_visible(not hide_details)
        self.outline_width_box.set_visible(not hide_details)
        self.outline_color_box.set_visible(not hide_details)

class PlaceholderTextView(Gtk.Overlay):
    def __init__(self, placeholder: str = "", hexpand: bool = True):
        super().__init__()

        self.text_view = Gtk.TextView(hexpand=hexpand, css_classes=["label-text-view"])
        self.set_child(self.text_view)

        self.placeholder_label = Gtk.Label(label=placeholder, css_classes=["dim-label"], halign=Gtk.Align.START, valign=Gtk.Align.CENTER,
                                           margin_start=9)
        self.add_overlay(self.placeholder_label)

        self.get_buffer().connect("changed", self.on_change_text)

    def get_buffer(self):
        return self.text_view.get_buffer()
    
    def on_change_text(self, buffer):
        start, end = buffer.get_bounds()
        text = buffer.get_text(start, end, False)
        self.placeholder_label.set_visible(text == "")

class TextView(Gtk.Box):
    def __init__(self, placeholder: str = "", **kwargs):
        super().__init__(css_classes=["linked"], **kwargs)

        self.entry = PlaceholderTextView(placeholder=placeholder, hexpand=True)
        self.revert_button = RevertButton()

        # self.entry.get_style_context().add_class("text-view")
        self.entry.text_view.add_css_class("round-left")

        self.append(self.entry)
        self.append(self.revert_button)

    def set_revert_visible(self, visible: bool):
        self.revert_button.set_visible(visible)
        if visible:
            self.entry.text_view.remove_css_class("round-right")
        else:
            self.entry.text_view.add_css_class("round-right")

class ColorChooserButton(Gtk.Box):
    def __init__(self, **kwargs):
        super().__init__(css_classes=["linked"], **kwargs)

        self.button = Gtk.ColorButton()
        self.revert_button = RevertButton()

        self.append(self.button)
        self.append(self.revert_button)

class FontChooserButton(Gtk.Box):
    def __init__(self, **kwargs):
        super().__init__(css_classes=["linked"], **kwargs)

        self.button = Gtk.FontButton()
        self.revert_button = RevertButton()

        self.append(self.button)
        self.append(self.revert_button)


class SpinButton(Gtk.Box):
    def __init__(self, start: float, end: float, step: float, **kwargs):
        super().__init__(css_classes=["linked"], **kwargs)

        self.button = Gtk.SpinButton.new_with_range(start, end, step)
        self.revert_button = RevertButton()

        self.append(self.button)
        self.append(self.revert_button)
