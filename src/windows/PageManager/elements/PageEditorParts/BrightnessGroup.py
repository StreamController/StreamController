"""
Author: Core447
Year: 2024

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
any later version.

This programm comes with ABSOLUTELY NO WARRANTY!

You should have received a copy of the GNU General Public License
along with this program. If not, see <https://www.gnu.org/licenses/>.
"""
from typing import TYPE_CHECKING

import gi

import globals as gl
from GtkHelper.GtkHelper import BetterExpander, better_disconnect
from GtkHelper.ScaleRow import ScaleRow
from src.windows.PageManager.elements.PageEditorBase import PageEditorGroup

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import GLib

if TYPE_CHECKING:
    from src.windows.PageManager.elements.PageEditor import PageEditor


class BrightnessGroup(PageEditorGroup):
    def __init__(self, page_editor: "PageEditor"):
        super().__init__(page_editor, title="Brightness Override")

    def build(self):
        self.enable_expander = BetterExpander(
            title="Overwrite Brightness",
            subtitle="Overrides the Deck Brightness",
            expanded=False,
            show_enable_switch=True
        )
        self.add(self.enable_expander)

        self.brightness_scale = ScaleRow(0, 0, 100, digits=0, draw_value=True, draw_side_values=False, title="Brightness")
        self.enable_expander.add_row(self.brightness_scale)

    def connect_events(self):
        self.enable_expander.connect("notify::enable-expansion", self.on_enable_changed)
        self.brightness_scale.scale.connect("value-changed", self.on_brightness_changed)

    def disconnect_events(self):
        better_disconnect(self.enable_expander, self.on_enable_changed)
        better_disconnect(self.brightness_scale.scale, self.on_brightness_changed)

    def load_config_settings(self, page_path: str):
        settings = gl.page_manager.get_brightness_settings(page_path)

        self.enable_expander.set_enable_expansion(settings.get("overwrite", False))
        self.enable_expander.set_expanded(settings.get("overwrite", False))

        self.brightness_scale.set_value(settings.get("value", 75))

    def on_enable_changed(self, *args):
        gl.page_manager.overwrite_brightness_settings(
            path=self.page_editor.active_page_path,
            overwrite=self.enable_expander.get_enable_expansion()
        )
        self.update_brightness()

    def on_brightness_changed(self, *args):
        gl.page_manager.overwrite_brightness_settings(
            path=self.page_editor.active_page_path,
            brightness=self.brightness_scale.get_value()
        )
        self.update_brightness()

    def update_brightness(self):
        def on_idle():
            for controller in gl.deck_manager.deck_controller:
                if controller.active_page.json_path == self.page_editor.active_page_path:
                    controller.load_brightness(controller.active_page)

        GLib.idle_add(on_idle)
