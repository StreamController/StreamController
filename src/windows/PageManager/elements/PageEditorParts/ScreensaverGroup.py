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
from src.backend.DeckManagement.ImageHelpers import image2pixbuf
from src.windows.PageManager.elements.PageEditorBase import PageEditorGroup

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, GLib, Gtk

if TYPE_CHECKING:
    from src.windows.PageManager.elements.PageEditor import PageEditor


class ScreensaverGroup(PageEditorGroup):
    def __init__(self, page_editor: "PageEditor"):
        super().__init__(page_editor, title="Screensaver Overwrite")

    def build(self):
        self.overwrite_expander = BetterExpander(
            title="Overwrite Screensaver",
            subtitle="Overrides the Deck Screensaver",
            expanded=False,
            show_enable_switch=True
        )
        self.add(self.overwrite_expander)

        self.media_main_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        self.overwrite_expander.add_row(self.media_main_box)

        self.media_settings_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, hexpand=True, valign=Gtk.Align.CENTER)
        self.media_main_box.append(self.media_settings_box)

        self.enable_screensaver_toggle = Adw.SwitchRow(title="Enable Screensaver")
        self.media_settings_box.append(self.enable_screensaver_toggle)

        self.delay_spin = Adw.SpinRow.new_with_range(1, 60, 1)
        self.delay_spin.set_title("Delay (min)")
        self.media_settings_box.append(self.delay_spin)

        self.loop_toggle = Adw.SwitchRow(title="Loop")
        self.media_settings_box.append(self.loop_toggle)

        self.fps_spin = Adw.SpinRow.new_with_range(0, 30, 1)
        self.fps_spin.set_title("FPS")
        self.media_settings_box.append(self.fps_spin)

        self.brightness_scale = ScaleRow(
            0, 0, 100,draw_side_values=False, draw_value=True, digits=0, title="Brightness"
        )
        self.media_settings_box.append(self.brightness_scale)

        self.button_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, hexpand=True, valign=Gtk.Align.CENTER)
        self.media_main_box.append(self.button_box)

        self.media_selector_button = Gtk.Button(
            label="Select",
            css_classes=["page-settings-media-selector"],
            halign=Gtk.Align.CENTER,
        )
        self.button_box.append(self.media_selector_button)

        self.media_selector_image = Gtk.Image()

    def connect_events(self):
        self.overwrite_expander.connect("notify::enable-expansion", self.on_overwrite_changed)
        self.enable_screensaver_toggle.connect("notify::active", self.on_enable_changed)
        self.delay_spin.connect("changed", self.on_delay_changed)
        self.loop_toggle.connect("notify::active", self.on_loop_changed)
        self.fps_spin.connect("changed", self.on_fps_changed)
        self.brightness_scale.scale.connect("value-changed", self.on_brightness_changed)
        self.media_selector_button.connect("clicked", self.on_media_selector_click)

    def disconnect_events(self):
        better_disconnect(self.overwrite_expander, self.on_overwrite_changed)
        better_disconnect(self.enable_screensaver_toggle, self.on_enable_changed)
        better_disconnect(self.delay_spin, self.on_delay_changed)
        better_disconnect(self.loop_toggle, self.on_loop_changed)
        better_disconnect(self.fps_spin, self.on_fps_changed)
        better_disconnect(self.brightness_scale, self.on_brightness_changed)
        better_disconnect(self.media_selector_button, self.on_media_selector_click)

    def load_config_settings(self, page_path: str):
        screensaver_settings = gl.page_manager.get_screensaver_settings(page_path)

        self.overwrite_expander.set_enable_expansion(screensaver_settings.get("overwrite", False))
        self.overwrite_expander.set_expanded(screensaver_settings.get("overwrite", False))

        self.enable_screensaver_toggle.set_active(screensaver_settings.get("enable", False))
        self.delay_spin.set_value(screensaver_settings.get("time-delay", 5))
        self.loop_toggle.set_active(screensaver_settings.get("loop", False))
        self.fps_spin.set_value(screensaver_settings.get("fps", 30))
        self.brightness_scale.set_value(screensaver_settings.get("brightness", 75))

        self.set_thumbnail(screensaver_settings.get("media-path", None))

    def on_overwrite_changed(self, *args):
        gl.page_manager.overwrite_screensaver_settings(
            path=self.page_editor.active_page_path,
            overwrite=self.overwrite_expander.get_enable_expansion()
        )
        self.update_screensaver()

    def on_enable_changed(self, *args):
        gl.page_manager.overwrite_screensaver_settings(
            path=self.page_editor.active_page_path,
            enable=self.enable_screensaver_toggle.get_active()
        )
        self.update_screensaver()

    def on_delay_changed(self, *args):
        gl.page_manager.overwrite_screensaver_settings(
            path=self.page_editor.active_page_path,
            time_delay=int(self.delay_spin.get_value())
        )
        self.update_screensaver()

    def on_loop_changed(self, *args):
        gl.page_manager.overwrite_screensaver_settings(
            path=self.page_editor.active_page_path,
            loop=self.loop_toggle.get_active()
        )
        self.update_screensaver()

    def on_fps_changed(self, *args):
        gl.page_manager.overwrite_screensaver_settings(
            path=self.page_editor.active_page_path,
            fps=int(self.fps_spin.get_value())
        )
        self.update_screensaver()

    def on_brightness_changed(self, *args):
        gl.page_manager.overwrite_screensaver_settings(
            path=self.page_editor.active_page_path,
            brightness=self.brightness_scale.get_value()
        )
        self.update_screensaver()

    def on_media_selector_click(self, *args):
        screensaver_settings = gl.page_manager.get_screensaver_settings(self.page_editor.active_page_path)

        gl.app.let_user_select_asset(default_path=screensaver_settings.get("media-path", ""), callback_func=self.update_image)

    def set_thumbnail(self, file_path):
        if not file_path:
            self.media_selector_image.set_from_pixbuf(None)
            self.media_selector_image.pixbuf = None
            return

        image = gl.media_manager.get_thumbnail(file_path)
        pixbuf = image2pixbuf(image)

        self.media_selector_image.set_from_pixbuf(pixbuf)
        self.media_selector_button.set_child(self.media_selector_image)

        image.close()

    def update_image(self, file_path):
        self.set_thumbnail(file_path)

        gl.page_manager.overwrite_screensaver_settings(
            path=self.page_editor.active_page_path,
            media_path=file_path
        )

        self.update_screensaver()

    def update_screensaver(self):
        def on_idle():
            for controller in gl.deck_manager.deck_controller:
                if controller.active_page.json_path == self.page_editor.active_page_path:
                    controller.load_screensaver(controller.active_page)

        GLib.idle_add(on_idle)
