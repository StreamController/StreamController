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
    def __init__(self, sidebar, **kwargs):
        super().__init__(**kwargs)
        self.sidebar = sidebar
        self.build()

    def build(self):
        self.overlay = Gtk.Overlay()
        self.append(self.overlay)

        self.button = Gtk.Button(label="Select", css_classes=["icon-selector", "key-image", "no-padding"], overflow=Gtk.Overflow.HIDDEN)
        self.button.connect("clicked", self.on_click)
        # self.append(self.button)
        self.overlay.set_child(self.button)

        self.button_fixed = Gtk.Fixed()
        self.button.set_child(self.button_fixed)

        self.image = Gtk.Image(overflow=Gtk.Overflow.HIDDEN, css_classes=["key-image", "icon-selector-image-normal"])
        # self.button.set_child(self.image)
        self.button_fixed.put(self.image, 0, 0)

        self.label = Gtk.Label(label=gl.lm.get("icon-selector-click-hint"), css_classes=["icon-selector-hint-label-hidden"])
        label_size = self.label.get_preferred_size()[1] # 1 for natural size
        label_width, label_height = label_size.width, label_size.height
        self.button_fixed.put(self.label, (175-label_width)/2, (175-label_height)/2) # 175 for the size of the image

        # Hover controller - css doesn't work because a :hover on the image would leave if focus switches to label
        motion_controller = Gtk.EventControllerMotion()
        motion_controller.connect("enter", self.on_hover_enter)
        motion_controller.connect("leave", self.on_hover_leave)

        self.button.add_controller(motion_controller)

        # Remove button overlay
        self.remove_button = Gtk.Button(icon_name="com.core447.StreamController_entry-delete", valign=Gtk.Align.END, halign=Gtk.Align.END,
                                        css_classes=["icon-selector-remove-button", "no-padding", "remove-button"],
                                        visible=False)
        self.remove_button.connect("clicked", self.remove_media)
        self.overlay.add_overlay(self.remove_button)
        self.overlay.set_clip_overlay(self.remove_button, True)



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
        media_path = self.get_media_path()
        gl.app.let_user_select_asset(default_path = media_path, callback_func=self.set_media_callback)

    def get_media_path(self):
        active_page_dict = self.sidebar.main_window.leftArea.deck_stack.get_visible_child().deck_controller.active_page.dict
        active_coords:tuple = self.sidebar.active_coords
        page_coords = f"{active_coords[0]}x{active_coords[1]}"

        if "keys" not in active_page_dict:
            return None
        if page_coords not in active_page_dict["keys"]:
            return None
        if "media" not in active_page_dict["keys"][page_coords]:
            return None
        if "path" not in active_page_dict["keys"][page_coords]["media"]:
            return None
        return active_page_dict["keys"][page_coords]["media"]["path"]
    
    def set_media_path(self, path):
        active_page:dict = self.sidebar.main_window.leftArea.deck_stack.get_visible_child().deck_controller.active_page
        active_coords:tuple = self.sidebar.active_coords
        page_coords = f"{active_coords[0]}x{active_coords[1]}"

        active_page.dict.setdefault("keys", {})
        active_page.dict["keys"].setdefault(page_coords, {})
        active_page.dict["keys"][page_coords].setdefault("media", {
            "path": None,
            "loop": True,
            "fps": 30
        })
        active_page.dict["keys"][page_coords]["media"]["path"] = path

        # Save page
        active_page.save()

        # Update remove button visibility
        if path not in [None, ""]:
            self.remove_button.set_visible(True)

    def set_media_callback(self, path):
        self.set_media_path(path)
        # Reload key
        controller = self.sidebar.main_window.leftArea.deck_stack.get_visible_child().deck_controller
        key_index = controller.coords_to_index(self.sidebar.active_coords)
        controller.load_key(key_index, page=controller.active_page)

    def remove_media(self, *args):
        # Get keygrid of active controller
        controller = self.sidebar.main_window.leftArea.deck_stack.get_visible_child().deck_controller
        grid = controller.get_own_key_grid()
        # Call keys remove method
        grid.selected_key.remove_media()
        # Hide remove button
        self.remove_button.set_visible(False)

    def has_image_to_remove(self):
        return self.get_media_path() is not None
    
    def load_for_coords(self, coords):
        self.remove_button.set_visible(self.has_image_to_remove())