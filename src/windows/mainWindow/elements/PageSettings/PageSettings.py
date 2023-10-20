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
from gi.repository import Gtk, Adw, GLib, Gdk, GdkPixbuf

# Import Python modules 
from loguru import logger as log
import numpy
import cv2
import threading
from time import sleep
from math import floor

# Import globals
import globals as gl

# Import own modules
from src.backend.DeckManagement.ImageHelpers import image2pixbuf, is_transparent
from src.windows.mainWindow.elements.PageSettings.BackgroundGroup import BackgroundGroup
from src.windows.mainWindow.elements.PageSettings.DeckGroup import DeckGroup


class PageSettings(Gtk.Box):
    def __init__(self, deck_page, **kwargs):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, hexpand=True, vexpand=True,
                         margin_start=50, margin_end=50,
                         margin_top=50, margin_bottom=50)
        # self.set_halign(Gtk.Align.CENTER)
        self.deck_page = deck_page
        self.build()

    def build(self):
        self.scrolled_window = Gtk.ScrolledWindow(hexpand=True, vexpand=True)
        self.append(self.scrolled_window)

        clamp = Adw.Clamp()
        self.scrolled_window.set_child(clamp)

        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, hexpand=True)
        clamp.set_child(main_box)
        
        settings_group = DeckGroup(self)
        main_box.append(settings_group)

        background_group = BackgroundGroup(self)
        main_box.append(background_group)

class BrightnessRow(Adw.PreferencesRow):
    def __init__(self, page_settings: PageSettings, **kwargs):
        super().__init__()
        self.page_settings = page_settings
        self.build()

    def build(self):
        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, hexpand=True,
                                margin_start=15, margin_end=15, margin_top=15, margin_bottom=15)
        self.set_child(self.main_box)

        self.label = Gtk.Label(label="Brightness", hexpand=True, xalign=0)
        self.main_box.append(self.label)

        self.scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, min=0, max=100, step=1)
        self.scale.set_draw_value(True)
        self.set_scale_initial_value()
        self.scale.connect("value-changed", self.on_value_changed)
        self.main_box.append(self.scale)


    def set_scale_initial_value(self):
        # Load default scalar value
        current_page = None
        if hasattr(self.page_settings.deck_page.deck_controller, "active_page"):
            current_page = self.page_settings.deck_page.deck_controller.active_page
        self.set_scale_from_page(current_page)

    def set_scale_from_page(self, page):
        if page == None:
            self.scale.set_sensitive(False)
            self.main_box.append(Gtk.Label(label="Error", hexpand=True, xalign=0, css_classes=["red-color"]))
            return

        brightness = page["brightness"]
        self.scale.set_value(brightness)

    def on_value_changed(self, scale):
        value = round(scale.get_value())
        # update value in page
        self.page_settings.deck_page.deck_controller.active_page["brightness"] = value
        self.page_settings.deck_page.deck_controller.active_page.save()
        # update deck without reload of page
        self.page_settings.deck_page.deck_controller.set_brightness(value)

class SwitchSetting(Adw.PreferencesRow):
    def __init__(self, label, **kwargs):
        super().__init__()
        self.label = label
        self.build()

    def build(self):
        self.main_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, hexpand=True)
        self.set_child(self.main_box)

        self.main_box.append(Gtk.Label(label=self.label, hexpand=True, xalign=0, margin_top=15, margin_bottom=15, margin_start=15))
        self.switch = Gtk.Switch(margin_bottom=15, margin_top=15, margin_end=15)
        self.main_box.append(self.switch)

class ScaleSetting(Adw.PreferencesRow):
    def __init__(self, label, min=0, max=100, step=1, **kwargs):
        super().__init__()
        self.label = label
        self.min, self.max, self.step = min, max, step
        self.build()

    def build(self):
        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, hexpand=True)
        self.set_child(self.main_box)

        self.main_box.append(Gtk.Label(label=self.label, hexpand=True, xalign=0, margin_top=15, margin_start=15))
        self.scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, min=self.min, max=self.max, step=self.step)
        self.main_box.append(self.scale)

        self.scale.set_draw_value(True)



class TestBox(Gtk.Box):
    def __init__(self, **kwargs):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, hexpand=True, vexpand=True, css_classes=["settings-box"])
        self.set_valign(Gtk.Align.CENTER)
        self.build()

    def build(self):
        l = Gtk.Label(label="Test Box")
        self.append(l)