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

from PIL import Image

from src.backend.DeckManagement.InputIdentifier import Input, InputIdentifier
from src.backend.DeckManagement.HelperMethods import add_default_keys

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
    def __init__(self, sidebar, **kwargs):
        super().__init__(**kwargs)
        self.sidebar = sidebar
        self.active_identifier: InputIdentifier = None
        self.active_state: int = None
        self.build()

    def build(self):
        self.overlay = Gtk.Overlay()
        self.append(self.overlay)

        self.button = Gtk.Button(label="Select", css_classes=["icon-selector" "key-image", "no-padding"], overflow=Gtk.Overflow.HIDDEN)
        self.button.connect("clicked", self.on_click)
        # self.append(self.button)
        self.overlay.set_child(self.button)

        self.button_fixed = Gtk.Overlay()
        self.button.set_child(self.button_fixed)

        self.image = Gtk.Picture(overflow=Gtk.Overflow.HIDDEN, css_classes=["key-image", "icon-selector-image-base", "icon-selector-image-key"])
        # self.button.set_child(self.image)
        self.button_fixed.set_child(self.image)

        self.label = Gtk.Label(label=gl.lm.get("icon-selector-click-hint"), css_classes=["icon-selector-hint-label-hidden"],
                               halign=Gtk.Align.CENTER, valign=Gtk.Align.CENTER)
        # label_size = self.label.get_preferred_size()[1] # 1 for natural size
        # label_width, label_height = label_size.width, label_size.height
        # self.button_fixed.put(self.label, (175-label_width)/2, (175-label_height)/2) # 175 for the size of the image
        self.button_fixed.add_overlay(self.label)

        # Hover controller - css doesn't work because a :hover on the image would leave if focus switches to label
        motion_controller = Gtk.EventControllerMotion()
        motion_controller.connect("enter", self.on_hover_enter)
        motion_controller.connect("leave", self.on_hover_leave)

        self.button.add_controller(motion_controller)

        # Remove button overlay
        self.remove_button = Gtk.Button(icon_name="user-trash-symbolic", valign=Gtk.Align.END, halign=Gtk.Align.END,
                                        css_classes=["icon-selector-remove-button", "no-padding", "remove-button"],
                                        visible=False)
        self.remove_button.connect("clicked", self.remove_media)
        self.overlay.add_overlay(self.remove_button)
        self.overlay.set_clip_overlay(self.remove_button, True)



    def set_image(self, image):
        pixbuf = image2pixbuf(image.convert("RGBA"), force_transparency=True)
        GLib.idle_add(self.image.set_pixbuf, pixbuf, priority=GLib.PRIORITY_HIGH)

    def on_hover_enter(self, *args):
        self.label.set_css_classes(["icon-selector-hint-label-visible"])
        self.image.add_css_class("icon-selector-image-hover")

    def on_hover_leave(self, *args):
        self.label.set_css_classes(["icon-selector-hint-label-hidden"])
        self.image.remove_css_class("icon-selector-image-hover")

    def on_click(self, button):
        media_path = self.get_media_path()
        GLib.idle_add(gl.app.let_user_select_asset, media_path, self.set_media_callback)

    def get_media_path(self):
        page = gl.app.main_win.get_active_page()
        if page is None:
            return
        
        active_state = self.sidebar.active_state

        return page.get_media_path(identifier=self.active_identifier, state=active_state)
    
    def set_media_path(self, path):
        page = gl.app.main_win.get_active_page()
        if page is None:
            return

        page.set_media_path(identifier=self.active_identifier, state=self.active_state, path=path)
        page.save()

        # Update remove button visibility
        self.remove_button.set_visible(path not in [None, ""])

    def set_media_callback(self, path):
        self.set_media_path(path)
        # Reload key
        controller = gl.app.main_win.get_active_controller()
        if controller is None:
            return

        c_input = controller.get_input(self.sidebar.active_identifier)
        c_input.load_from_page(controller.active_page)

    def remove_media(self, *args):
        self.set_media_callback(None)

    def has_image_to_remove(self):
        return self.get_media_path() is not None
    
    def load_for_identifier(self, identifier: InputIdentifier, state: int):
        self.active_identifier = identifier
        self.active_state = state

        ## Set aspect ratio
        if isinstance(identifier, Input.Dial):
            self.image.remove_css_class("icon-selector-image-key")
            self.image.add_css_class("icon-selector-image-dial")
        else:
            self.image.remove_css_class("icon-selector-image-dial")
            self.image.add_css_class("icon-selector-image-key")

        self.remove_button.set_visible(self.has_image_to_remove())