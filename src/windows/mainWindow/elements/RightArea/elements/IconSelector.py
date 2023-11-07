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
import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, GLib

# Import Python modules
from loguru import logger as log

# Import own modules
from src.backend.DeckManagement.ImageHelpers import image2pixbuf

# Import globals
import globals as gl

class IconSelector(Gtk.Box):
    def __init__(self, right_area, **kwargs):
        super().__init__(**kwargs)
        self.right_area = right_area
        self.build()

    def build(self):
        self.button = Gtk.Button(label="Select", css_classes=["icon-selector", "key-image", "no-padding"])
        self.button.connect("clicked", self.on_click)

        self.button_fixed = Gtk.Fixed()
        self.button.set_child(self.button_fixed)

        self.image = Gtk.Image(overflow=Gtk.Overflow.HIDDEN, css_classes=["key-image", "icon-selector-image-normal"])
        # self.button.set_child(self.image)
        self.button_fixed.put(self.image, 0, 0)

        self.label = Gtk.Label(label="Click to change", css_classes=["icon-selector-hint-label-hidden"])
        label_size = self.label.get_preferred_size()[1] # 1 for natural size
        label_width, label_height = label_size.width, label_size.height
        self.button_fixed.put(self.label, (175-label_width)/2, (175-label_height)/2) # 175 for the size of the image

        # Hover controller - css doesn't work because a :hover on the image would leave if focus switches to label
        motion_controller = Gtk.EventControllerMotion()
        motion_controller.connect("enter", self.on_hover_enter)
        motion_controller.connect("leave", self.on_hover_leave)

        self.button.add_controller(motion_controller)

        self.append(self.button)

    def set_image(self, image):
        pixbuf = image2pixbuf(image.convert("RGBA"), force_transparency=True)
        GLib.idle_add(self.image.new_from_pixbuf, pixbuf)

    def on_hover_enter(self, *args):
        self.label.set_css_classes(["icon-selector-hint-label-visible"])
        self.image.remove_css_class("icon-selector-image-normal")
        self.image.add_css_class("icon-selector-image-hover")

    def on_hover_leave(self, *args):
        self.label.set_css_classes(["icon-selector-hint-label-hidden"])
        self.image.remove_css_class("icon-selector-image-hover")
        self.image.add_css_class("icon-selector-image-normal")

    def on_click(self, button):
        asset_manager = gl.app.asset_manager
        asset_manager.present()