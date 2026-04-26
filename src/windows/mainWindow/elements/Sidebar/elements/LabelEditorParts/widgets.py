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
import gi

import globals as gl
from GtkHelper.GtkHelper import RevertButton

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk


class TextEntry(Gtk.Box):
    def __init__(self, **kwargs):
        super().__init__(css_classes=["linked"], margin_end=5,  **kwargs)

        self.entry = Gtk.Entry(hexpand=True,placeholder_text=gl.lm.get("label-editor-placeholder-text"))
        self.revert_button = RevertButton()

        self.append(self.entry)
        self.append(self.revert_button)

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


class AlignmentButtons(Gtk.Box):
    def __init__(self, **kwargs):
        super().__init__(css_classes=["linked"], **kwargs)

        self.left_button = Gtk.ToggleButton(icon_name="format-justify-left-symbolic", tooltip_text="Left")
        self.center_button = Gtk.ToggleButton(icon_name="format-justify-center-symbolic", tooltip_text="Center")
        self.right_button = Gtk.ToggleButton(icon_name="format-justify-right-symbolic", tooltip_text="Right")

        # Group the toggle buttons so only one can be active
        self.center_button.set_group(self.left_button)
        self.right_button.set_group(self.left_button)

        self.revert_button = RevertButton()

        self.append(self.left_button)
        self.append(self.center_button)
        self.append(self.right_button)
        self.append(self.revert_button)

    def get_alignment(self) -> str:
        if self.left_button.get_active():
            return "left"
        elif self.right_button.get_active():
            return "right"
        else:
            return "center"

    def set_alignment(self, alignment: str):
        if alignment == "left":
            self.left_button.set_active(True)
        elif alignment == "right":
            self.right_button.set_active(True)
        else:
            self.center_button.set_active(True)
