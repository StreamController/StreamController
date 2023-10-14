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
from gi.repository import Gtk, Adw

# Import Python modules 
from loguru import logger as log

class DeckSettings(Gtk.Box):
    def __init__(self, deck_page, **kwargs):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, hexpand=True, vexpand=True,
                         margin_start=50, margin_end=50,
                         margin_top=50, margin_bottom=50)
        # self.set_halign(Gtk.Align.CENTER)
        self.deck_page = deck_page
        self.build()

    def build(self):
        clamp = Adw.Clamp()
        self.append(clamp)

        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, hexpand=True)
        clamp.set_child(main_box)
        
        settings_group = Adw.PreferencesGroup(title="Deck Settings", description="Applies only to current page")
        main_box.append(settings_group)

        background_group = Adw.PreferencesGroup(title="Background", description="Applies only to current page", margin_top=15)
        main_box.append(background_group)

        settings_group.add(SwitchSetting("Enable Screensaver"))
        settings_group.add(ScaleSetting("Brightness", step=1))

        background_group.add(SwitchSetting("Enable Background"))


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