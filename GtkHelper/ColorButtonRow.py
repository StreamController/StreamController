from dataclasses import dataclass
from typing import Callable

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, Gdk, GLib, Gio

class ColorButtonRow(Adw.ActionRow):
    """
        Initializes a ColorButtonRow widget with a color button and optional title and subtitle.

        Parameters:
            title (str, optional): The title to display in the row.
            subtitle (str, optional): The subtitle to display below the title.
            default_color (tuple[int, int, int, int], optional): The default color to set for the color button in
                                                                RGBA format (default is black with full opacity).

        Description:
            This constructor creates a new ColorButtonRow widget. It sets up a Gtk.ColorButton for selecting
            a color and assigns it to the row. The initial color is set based on the provided `default_color`
            tuple, which represents the color in RGBA format (each value ranges from 0 to 255).

            Additionally, the color button is connected to the `color-set` signal, which triggers the `_on_color_changed`
            method when the color is modified. The color is stored internally as a tuple of integers representing
            the RGBA values.

            The row is set up with a title and subtitle if provided.
    """
    def __init__(self,
                 title: str = None,
                 subtitle: str = None,
                 default_color: tuple[int, int, int, int] = (0, 0, 0, 255),
                 ):
        super().__init__(title=title, subtitle=subtitle)

        self.color = default_color

        self.color_button = Gtk.ColorButton(valign=Gtk.Align.CENTER)

        self.color_button.connect("color-set", self._on_color_changed)

        self.add_suffix(self.color_button)

        self.set_color(self.color)

    def _on_color_changed(self, button: Gtk.ColorButton):
        self.color = self.get_color()

    def set_color(self, color: tuple[int, int, int, int]):
        """Sets the color from an int tuple"""
        self.color = color
        self.color_button.set_rgba(self.get_color_rgba())
        self.color_button.emit("color-set")

    def set_color_rgba(self, color: Gdk.RGBA):
        normalized = (round(color.red * 255),
                      round(color.green * 255),
                      round(color.blue * 255),
                      round(color.alpha * 255))
        self.color = normalized
        self.color_button.set_rgba(color)
        self.color_button.emit("color-set")

    def get_color_rgba(self) -> Gdk.RGBA:
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
        rgba = self.color_button.get_rgba()

        return (round(rgba.red * 255),
                round(rgba.green * 255),
                round(rgba.blue * 255),
                round(rgba.alpha * 255))