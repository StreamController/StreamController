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

from src.backend.DeckManagement.InputIdentifier import InputIdentifier
from src.backend.DeckManagement.HelperMethods import add_default_keys

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, Gdk, Pango

# Import Python modules
from loguru import logger as log

# Import globals
import globals as gl

class BackgroundEditor(Gtk.Box):
    def __init__(self, sidebar, **kwargs):
        self.sidebar = sidebar
        super().__init__(**kwargs)
        self.build()

    def build(self):
        self.clamp = Adw.Clamp()
        self.append(self.clamp)

        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, hexpand=True)
        self.clamp.set_child(self.main_box)

        self.label_group = BackgroundGroup(self.sidebar)
        self.main_box.append(self.label_group)

    def load_for_identifier(self, identifier: InputIdentifier, state: int):
        self.label_group.load_for_identifier(identifier, state)


class BackgroundGroup(Adw.PreferencesGroup):
    def __init__(self, sidebar, **kwargs):
        super().__init__(**kwargs)
        self.sidebar = sidebar

        self.build()

    def build(self):
        self.expander = BackgroundExpanderRow(self)
        self.add(self.expander)

        return

    def load_for_identifier(self, identifier: InputIdentifier, state: int):
        self.expander.load_for_identifier(identifier, state)

class BackgroundExpanderRow(Adw.ExpanderRow):
    def __init__(self, label_group):
        super().__init__(title=gl.lm.get("background-editor.header"), subtitle=gl.lm.get("background-editor-expander.subtitle"))
        self.label_group = label_group
        self.active_identifier: InputIdentifier = None
        self.active_state = None
        self.build()

    def build(self):
        self.color_row = ColorRow(sidebar=self.label_group.sidebar, expander=self)
        self.add_row(self.color_row)

        self.reset_color_button = ResetColorButton(color_row=self.color_row)
        self.add_row(self.reset_color_button)

    def load_for_identifier(self, identifier: InputIdentifier, state: int):
        self.active_identifier = identifier
        self.active_state = state

        self.color_row.load_for_identifier(identifier, state)
        self.reset_color_button.update()

class ColorRow(Adw.PreferencesRow):
    def __init__(self, sidebar, expander: BackgroundExpanderRow, **kwargs):
        super().__init__(**kwargs)
        self.sidebar = sidebar
        self.expander = expander
        self.active_identifier: InputIdentifier = None
        self.active_state = None
        self.build()

    def build(self):
        self.main_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, hexpand=True,
                                margin_start=15, margin_end=15, margin_top=15, margin_bottom=15)
        self.set_child(self.main_box)

        self.label = Gtk.Label(label=gl.lm.get("background-editor.color.label"), xalign=0, hexpand=True)
        self.main_box.append(self.label)
        self.color_chooser_button = Gtk.ColorDialogButton()
        self.main_box.append(self.color_chooser_button)

        self.color_dialog = Gtk.ColorDialog(title=gl.lm.get("background-editor.color.dialog.title"))

        self.color_chooser_button.set_dialog(self.color_dialog)

        self.connect_signals()

    def connect_signals(self):
        self.color_chooser_button.connect("notify::rgba", self.on_change_color)

    def disconnect_signals(self):
        try:
            self.color_chooser_button.disconnect_by_func(self.on_change_color)
        except:
            pass

    def set_color(self, color_values: list):
        if len(color_values) == 3:
            color_values.append(255)
        color = Gdk.RGBA()
        color.parse(f"rgba({color_values[0]}, {color_values[1]}, {color_values[2]}, {color_values[3]})")
        self.color_chooser_button.set_rgba(color)

    def on_change_color(self, *args):
        color = self.color_chooser_button.get_rgba()
        green = round(color.green * 255)
        blue = round(color.blue * 255)
        red = round(color.red * 255)
        alpha = round(color.alpha * 255)

        active_page = gl.app.main_win.get_active_page()
        active_page.set_background_color(identifier=self.active_identifier, state=self.active_state, color=[red, green, blue, alpha])

        self.expander.reset_color_button.update()

    def load_for_identifier(self, identifier: InputIdentifier, state: int):
        self.disconnect_signals()

        self.active_identifier = identifier
        self.active_state = state

        active_page = gl.app.main_win.get_active_page()
        color = active_page.get_background_color(identifier=identifier, state=self.active_state)
        if color is None:
            color = [0, 0, 0, 0]

        self.set_color(color)

        self.connect_signals()

class ResetColorButton(Adw.PreferencesRow):
    def __init__(self, color_row: ColorRow, **kwargs):
        super().__init__(**kwargs, css_classes=["no-padding", "reset-button"])
        self.color_row: ColorRow = color_row

        self.button = Gtk.Button(hexpand=True, vexpand=True, overflow=Gtk.Overflow.HIDDEN,
                                 css_classes=["no-margin", "invisible"],
                                 label=gl.lm.get("background-editor.color.reset"),
                                 margin_bottom=5, margin_top=5)
        self.button.connect("clicked", self.on_click)
        self.set_child(self.button)

    def on_click(self, button):
        self.color_row.color_chooser_button.set_rgba(Gdk.RGBA(0, 0, 0, 0))

    def update(self):
        color = self.color_row.color_chooser_button.get_rgba()
        green = round(color.green * 255)
        blue = round(color.blue * 255)
        red = round(color.red * 255)
        alpha = round(color.alpha * 255)

        # Only show button if color is not the default of [0, 0, 0, 0]
        if [red, green, blue, alpha] == [0, 0, 0, 0]:
            self.set_visible(False)
        else:
            self.set_visible(True)