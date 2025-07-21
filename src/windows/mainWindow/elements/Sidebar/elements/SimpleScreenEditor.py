import os

from gi.repository import Gtk, Adw

from typing import TYPE_CHECKING

from src.backend.DeckManagement.InputIdentifier import Input
from src.windows.mainWindow.elements.Sidebar.elements.ActionManager import ActionManager

from PIL import Image

# Import globals
import globals as gl

from src.backend.DeckManagement.ImageHelpers import *

class SimpleScreenEditor(Gtk.Box):
    def __init__(self, sidebar, **kwargs):
        self.sidebar = sidebar
        super().__init__(**kwargs)
        self.build()

    def build(self):
        self.clamp = Adw.Clamp()
        self.append(self.clamp)

        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, hexpand=True)
        self.clamp.set_child(self.main_box)

        self.simple_screen_group = SimpleScreenGroup(self.sidebar)
        self.main_box.append(self.simple_screen_group)

class SimpleScreenGroup(Adw.PreferencesGroup):
    def __init__(self, sidebar, **kwargs):
        super().__init__(**kwargs)
        self.sidebar = sidebar

        self.build()

    def build(self):
        self.expander = SimpleScreenExpanderRow(self)
        self.add(self.expander)

        return

class SimpleScreenExpanderRow(Adw.ExpanderRow):
    def __init__(self, label_group):
        super().__init__(title=gl.lm.get("background-editor.header"), subtitle=gl.lm.get("background-editor-expander.subtitle"))
        self.label_group = label_group
        self.active_identifier: InputIdentifier = None
        self.active_state = None
        self.build()

    def build(self):
        self.image_row = ImageRow(sidebar=self.label_group.sidebar, expander=self)
        self.add_row(self.image_row)


class ImageRow(Adw.PreferencesRow):
    def __init__(self, sidebar, expander: SimpleScreenExpanderRow, **kwargs):
        super().__init__(**kwargs)
        self.sidebar = sidebar
        self.expander = expander
        self.active_identifier: InputIdentifier = None
        self.active_state = None
        self.build()
        self.define_handlers()

    def build(self):
        self.main_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, hexpand=True,
                                margin_start=15, margin_end=15, margin_top=15, margin_bottom=15)
        self.set_child(self.main_box)

        self.label = Gtk.Label(label=gl.lm.get("background-editor.color.label"),
                               xalign=0, hexpand=True)
        self.main_box.append(self.label)

        self.media_selector_image = Gtk.Image() # Will be bound to the button by self.set_thumbnail()

        self.media_selector_button = Gtk.Button(label=gl.lm.get("select"), css_classes=["page-settings-media-selector"])
        self.main_box.append(self.media_selector_button)

        self.color_dialog = Gtk.ColorDialog(title=gl.lm.get("background-editor.color.dialog.title"))

        # self.button.button.set_dialog(self.color_dialog)

    def define_handlers(self):
        self.media_selector_button.connect("clicked", self.on_choose_image)


    def on_choose_image(self, button):
        # self.settings_page.deck_page.deck_controller.active_page.dict.setdefault("background", {})
        media_path = None # self.settings_page.deck_page.deck_controller.active_page.dict["background"].setdefault("path", None)

        gl.app.let_user_select_asset(default_path=media_path, callback_func=self.set_deck_background)

    def set_deck_background(self, file_path: str) -> None:
        self.set_thumbnail(file_path)

        self.set_background_to_page(file_path)

        # self.set_ui_background(file_path)

    def set_thumbnail(self, file_path):
        if file_path == None:
            self.media_selector_image.clear()
            return
        if file_path is None:
            return
        if not os.path.isfile(file_path):
            return
        image = gl.media_manager.get_thumbnail(file_path)
        pixbuf = image2pixbuf(image)
        if pixbuf is None:
            # This usually means that the provided image is a non RGB one
            dial = Gtk.AlertDialog(
                message="The chosen image doesn't seem to have RGB color channels.",
                detail="Please convert it in an app like GIMP.",
                modal=True
            )
            dial.show()
            return
        self.media_selector_image.pixbuf = None
        del self.media_selector_image.pixbuf
        self.media_selector_image.set_from_pixbuf(pixbuf)
        self.media_selector_button.set_child(self.media_selector_image)


    def set_background_to_page(self, file_path):

        deck_controller = gl.app.main_win.get_active_page().deck_controller

        screen_size = deck_controller.get_screen_image_size()
        empty = Image.open(file_path).crop((0, 0) + screen_size) #new("RGB", screen_size, (0, 0, 0))
        native_image = PILHelper.to_native_screen_format(deck_controller.deck, empty)

        c_input = deck_controller.deck.set_screen_image(native_image) #.et_input(identifier)

        # TODO set image in preview

    def set_ui_background(self, filepath):
        breakpoint()
        active_ident = self.sidebar.active_identifier
        # TODO save in settings somwhow

