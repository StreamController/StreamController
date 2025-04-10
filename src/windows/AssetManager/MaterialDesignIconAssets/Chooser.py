"""
Author: gensyn
Year: 2025

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
any later version.

This programm comes with ABSOLUTELY NO WARRANTY!

You should have received a copy of the GNU General Public License
along with this program. If not, see <https://www.gnu.org/licenses/>.
"""
import gi
from gi.repository.Gdk import RGBA

from windows.AssetManager.MaterialDesignIconAssets.FlowBox import MaterialDesignIconsChooserFlowBox

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, GLib
from gi.repository.Gtk import ColorButton, Box, Label, Scale, Orientation, GestureClick

# Import own modules
from src.windows.AssetManager.ChooserPage import ChooserPage

# Import typing modules
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from src.windows.AssetManager.AssetManager import AssetManager

class MaterialDesignIconAssetChooser(ChooserPage):
    def __init__(self, asset_manager: "AssetManager"):
        super().__init__()
        self.asset_manager = asset_manager
        self.nav_box.remove(self.type_box)

        self.asset_chooser = MaterialDesignIconsChooserFlowBox(self, orientation=Gtk.Orientation.HORIZONTAL, hexpand=True)
        GLib.idle_add(self.scrolled_box.prepend, self.asset_chooser)

        self.search_entry.disconnect_by_func(self.on_search_changed)
        self.search_entry.connect("search-changed", self.on_search_changed_with_timeout)

        settings_box = Box()

        color_label = Label(label="Color:")

        self.color = ColorButton(hexpand=False, margin_start=5)
        rgba = RGBA()
        rgba.red = 1
        rgba.green = 1
        rgba.blue = 1
        rgba.alpha = 1
        self.color.set_rgba(rgba)
        self.color.connect("color-set", self.on_search_changed)

        opacity_label = Label(label="Opacity:", margin_start=10)

        self.opacity_value_label = Label(label="100", margin_start=5)

        self.opacity = Scale.new_with_range(Orientation.HORIZONTAL, 0, 100, 1)
        self.opacity.set_value(100)
        self.opacity.set_size_request(200, -1)
        self.opacity.connect("value-changed", self.on_change_opacity)

        # Gtk.Scale has a bug not emitting a "released" event
        # so this is a workaround
        opacity_gesture = GestureClick(propagation_phase=Gtk.PropagationPhase.CAPTURE)
        opacity_gesture.connect("released", self.on_opacity_button_released)
        opacity_box = Box()
        opacity_box.add_controller(opacity_gesture)
        opacity_box.append(self.opacity)

        settings_box.append(color_label)
        settings_box.append(self.color)
        settings_box.append(opacity_label)
        settings_box.append(opacity_box)
        settings_box.append(self.opacity_value_label)

        self.main_box.insert_child_after(settings_box, self.nav_box)

        self.timeout_id = None

        self.set_loading(False)

    def on_search_changed(self, *_):
        self.asset_chooser.on_search_changed()

    def on_opacity_button_released(self, *_, **__):
        self.asset_chooser.on_search_changed()
        return False

    def on_change_opacity(self, *_) -> None:
        self.opacity_value_label.set_label(str(int(self.opacity.get_value())))

    def on_search_changed_with_timeout(self, *_) -> None:
        if self.timeout_id is not None:
            GLib.source_remove(self.timeout_id)

        self.timeout_id = GLib.timeout_add(500, self.asset_chooser.on_search_changed)