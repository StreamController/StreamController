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
import threading

import gi

from src.windows.AssetManager.MaterialDesignIconAssets.AssetPreview import AssetPreview
from src.windows.AssetManager.MaterialDesignIcons import mdi_helper

gi.require_version("Gtk", "4.0")
from gi.repository import GLib
from gi.repository.Gdk import RGBA
from gi.repository.Gtk import ColorButton, Scale, Box, Label, Orientation, GestureClick, Align, FlowBox, \
    PropagationPhase, Button, Overflow

from loguru import logger as log


class MaterialDesignIconsChooserPaginator(FlowBox):
    def __init__(self, asset_chooser, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.set_orientation(Orientation.HORIZONTAL)
        self.set_hexpand(True)
        self.connect("child-activated", self.on_child_activated)

        self.items = mdi_helper.get_icon_names()
        self.filtered_items = self.items
        self.search_string = ""
        self.items_per_page = 20
        self.current_page = 0
        self.asset_chooser = asset_chooser

        settings_box = Box(orientation=Orientation.HORIZONTAL)
        button_box = Box(css_classes=["linked"], orientation=Orientation.HORIZONTAL)
        navigation_box = Box(orientation=Orientation.HORIZONTAL, halign=Align.END)
        set_and_nav_box = Box(orientation=Orientation.HORIZONTAL, hexpand=True)
        set_and_nav_box.append(settings_box)
        set_and_nav_box.append(Box(orientation=Orientation.HORIZONTAL, hexpand=True))
        set_and_nav_box.append(navigation_box)
        self.asset_chooser.main_box.insert_child_after(set_and_nav_box, self.asset_chooser.nav_box)

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

        # Scale has a bug not emitting a "released" event
        # so this is a workaround
        opacity_gesture = GestureClick(propagation_phase=PropagationPhase.CAPTURE)
        opacity_gesture.connect("released", self.on_search_changed)
        opacity_box = Box()
        opacity_box.add_controller(opacity_gesture)
        opacity_box.append(self.opacity)

        self.nav_label = Label(label=f"1-{self.items_per_page}/{len(self.filtered_items)}", margin_end=5)

        self.prev_button = Button(icon_name="go-previous")
        self.prev_button.connect("clicked", self.on_prev_clicked)

        self.next_button = Button(icon_name="go-next")
        self.next_button.connect("clicked", self.on_next_clicked)

        settings_box.append(color_label)
        settings_box.append(self.color)
        settings_box.append(opacity_label)
        settings_box.append(opacity_box)
        settings_box.append(self.opacity_value_label)
        button_box.append(self.prev_button)
        button_box.append(self.next_button)
        navigation_box.append(self.nav_label)
        navigation_box.append(button_box)

        self.update_view()

    def update_view(self):
        self.remove_all()

        rgba = self.color.get_rgba()
        color_list = int(rgba.red * 255), int(rgba.green * 255), int(rgba.blue * 255), 255
        color = f'#{int(color_list[0]):02X}{int(color_list[1]):02X}{int(color_list[2]):02X}'
        opacity = int(self.opacity.get_value())

        start_index = self.current_page * self.items_per_page
        end_index = start_index + self.items_per_page

        current_items = self.filtered_items[start_index:end_index]

        for item in current_items:
            path = mdi_helper.get_icon_path(item)

            asset = {
                "icon_path": mdi_helper.get_icon_svg(item, path, color, opacity),
                "name": item
            }
            preview = AssetPreview(asset=asset)

            GLib.idle_add(self.append, preview)

        self.prev_button.set_sensitive(self.current_page > 0)
        self.next_button.set_sensitive(end_index < len(self.filtered_items))

        first_item_of_page = self.current_page * self.items_per_page + 1
        last_item_of_page = min(first_item_of_page + self.items_per_page - 1, len(self.filtered_items))
        self.nav_label.set_label(f"{first_item_of_page}-{last_item_of_page}/{len(self.filtered_items)}")

    def on_prev_clicked(self, button):
        if self.current_page > 0:
            self.current_page -= 1
            self.update_view()

    def on_next_clicked(self, button):
        if (self.current_page + 1) * self.items_per_page < len(self.items):
            self.current_page += 1
            self.update_view()

    def on_change_opacity(self, *_) -> None:
        self.opacity_value_label.set_label(str(int(self.opacity.get_value())))

    def on_search_changed(self, *_):
        self.asset_chooser.set_loading(True)
        new_search_string = self.asset_chooser.search_entry.get_text()

        if new_search_string != self.search_string:
            self.search_string = new_search_string
            self.current_page = 0
            self.filtered_items = [item for item in self.items if self.search_string in item]

        self.update_view()
        self.asset_chooser.set_loading(False)
        GLib.idle_add(self.asset_chooser.search_entry.grab_focus)

    def on_child_activated(self, flow_box, child):
        if callable(self.asset_chooser.asset_manager.callback_func):
            callback_thread = threading.Thread(target=self.callback_thread, args=(), name="flow_box_callback_thread")
            callback_thread.start()

        self.asset_chooser.asset_manager.close()

    @log.catch
    def callback_thread(self):
        child: AssetPreview = self.get_selected_children()[0]
        self.asset_chooser.asset_manager.callback_func(child.asset["icon_path"],
                                                       *self.asset_chooser.asset_manager.callback_args,
                                                       **self.asset_chooser.asset_manager.callback_kwargs)
