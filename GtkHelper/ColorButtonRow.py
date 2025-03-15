from dataclasses import dataclass
from typing import Callable

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, Gdk, GLib, Gio

class ColorButtonRow(Adw.ActionRow):
    def __init__(self,
                 title: str = None,
                 subtitle: str = None,
                 default_color: tuple[int, int, int, int] = (0, 0, 0, 255),
                 ):
        super().__init__(title=title, subtitle=subtitle)

        self.color = default_color

        self.color_button = Gtk.ColorButton(hexpand=True)
        self.color_button.set_margin_top(5)
        self.color_button.set_margin_bottom(5)

        self.color_button.connect("color-set", self._on_color_changed)

        self.add_suffix(self.color_button)

    def _on_color_changed(self, button: Gtk.ColorButton):
        self.color = self.get_color()

    def set_color(self, color: tuple[int, int, int, int]):
        """Sets the color from an int tuple"""
        self.color = color
        self.color_button.set_rgba(self.get_color_rgba())
        self.color_button.emit("color-set")

    def set_color_rgba(self, color: Gdk.RGBA):
        """Sets the color from an rgba object"""
        normalized = (round(color.red * 255),
                      round(color.green * 255),
                      round(color.blue * 255),
                      round(color.alpha * 255))
        self.color = normalized
        self.color_button.set_rgba(color)
        self.color_button.emit("color-set")

    def get_color_rgba(self) -> Gdk.RGBA:
        """Returns the current color in the rgba format"""
        rgba = Gdk.RGBA()

        if self.color is None:
            return rgba

        normalized = tuple(color / 255.0 for color in self.color)
        rgba.red = normalized[0]
        rgba.green = normalized[1]
        rgba.blue = normalized[2]
        rgba.alpha = normalized[3]
        return rgba

    def get_color(self) -> tuple[int, int, int, int]:
        """Returns the current color as a tuple of ints"""
        rgba = self.color_button.get_rgba()

        return (round(rgba.red * 255),
                round(rgba.green * 255),
                round(rgba.blue * 255),
                round(rgba.alpha * 255))