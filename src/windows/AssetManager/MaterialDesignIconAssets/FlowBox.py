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

from windows.AssetManager.MaterialDesignIconAssets.AssetPreview import AssetPreview
from windows.AssetManager.MaterialDesignIcons import mdi_helper

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, GLib

import threading
from loguru import logger as log


class MaterialDesignIconsChooserFlowBox(Gtk.Box):
    def __init__(self, asset_chooser, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.set_orientation(Gtk.Orientation.HORIZONTAL)
        self.set_hexpand(True)

        self.asset_chooser = asset_chooser

        self.all_assets: list["AssetPreview"] = []

        self.build()

    def build(self):
        self.flow_box = Gtk.FlowBox(hexpand=True, orientation=Gtk.Orientation.HORIZONTAL)
        self.flow_box.connect("child-activated", self.on_child_activated)
        GLib.idle_add(self.append, self.flow_box)
        GLib.idle_add(self.flow_box.append, Gtk.Label(label="Please enter at least 3 letters."))
        return

    def show_for_path(self, path):
        i = 0
        while True:
            child = self.flow_box.get_child_at_index(i)
            if child == None:
                return
            if child.asset["internal-path"] == path:
                GLib.idle_add(self.flow_box.select_child, child)
                return
            i += 1

    def on_search_changed(self):
        self.asset_chooser.set_loading(True)
        self.flow_box.remove_all()

        search_string = self.asset_chooser.search_entry.get_text()
        rgba = self.asset_chooser.color.get_rgba()
        color_list = int(rgba.red * 255), int(rgba.green * 255), int(rgba.blue * 255), 255
        color = f'#{int(color_list[0]):02X}{int(color_list[1]):02X}{int(color_list[2]):02X}'
        opacity = int(self.asset_chooser.opacity.get_value())

        if len(search_string) < 3:
            GLib.idle_add(self.flow_box.append, Gtk.Label(label="Please enter at least 3 letters."))
        else:
            for name in mdi_helper.get_icon_names():
                if search_string not in name:
                    continue

                path = mdi_helper.get_icon_path(name)

                asset = {
                    "icon_path": mdi_helper.get_icon_svg(name, path, color, opacity),
                    "name": name
                }
                asset = AssetPreview(flow=self, asset=asset)
                GLib.idle_add(self.flow_box.append, asset)
        self.asset_chooser.set_loading(False)
        GLib.idle_add(self.asset_chooser.search_entry.grab_focus)

    def on_child_activated(self, flow_box, child):
        if callable(self.asset_chooser.asset_manager.callback_func):
            callback_thread = threading.Thread(target=self.callback_thread, args=(), name="flow_box_callback_thread")
            callback_thread.start()

        self.asset_chooser.asset_manager.close()

    @log.catch
    def callback_thread(self):
        child = self.flow_box.get_selected_children()[0]
        self.asset_chooser.asset_manager.callback_func(child.asset["icon_path"],
                                                       *self.asset_chooser.asset_manager.callback_args,
                                                       **self.asset_chooser.asset_manager.callback_kwargs)
