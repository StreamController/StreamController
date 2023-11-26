"""
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
from gi.repository import Gtk, Adw, GLib, Gio, Gdk, GObject, GdkPixbuf

# Import python modules
import webbrowser as web
import asyncio
import threading

# Import own modules
from src.windows.Store.StorePage import StorePage
from src.windows.Store.Batches import OfficialBatch, VerifiedBatch
from src.backend.DeckManagement.ImageHelpers import image2pixbuf
from src.backend.DeckManagement.HelperMethods import is_video

# Typing
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from src.windows.Store.Store import Store


class PluginPage(StorePage):
    def __init__(self, store: "Store"):
        super().__init__(store=store)
        self.store = store
        self.search_entry.set_placeholder_text("Search for plugins")

        threading.Thread(target=self.load).start()

    def load(self):
        self.set_loading()
        plugins = self.store.backend.get_all_plugins()
        for plugin in plugins:
            GLib.idle_add(self.flow_box.append, PluginPreview(plugin_page=self, plugin_dict=plugin))

        self.set_loaded()



class PluginPreview(Gtk.FlowBoxChild):
    def __init__(self, plugin_page: PluginPage, plugin_dict: dict):
        super().__init__()
        self.plugin_page = plugin_page
        self.plugin_dict = plugin_dict

        self.stars = self.plugin_dict["stargazers"]

        self.build()

    def build(self):
        self.overlay = Gtk.Overlay()
        self.set_child(self.overlay)

        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL,
                                 hexpand=True, vexpand=False,
                                 css_classes=["no-padding"],
                                 width_request=250, height_request=250)
        self.set_child(self.main_box)

        self.main_button = Gtk.Button(hexpand=True, vexpand=False,
                                      width_request=250, height_request=200,
                                      css_classes=["no-padding", "no-round-bottom"])
        self.main_box.append(self.main_button)
        
        self.main_button_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL,
                                       hexpand=True, vexpand=False)
        self.main_button.set_child(self.main_button_box)
        
        self.image = Gtk.Picture(hexpand=True,
                                 content_fit=Gtk.ContentFit.COVER,
                                 height_request=90, width_request=250,
                                 css_classes=["plugin-store-image"])
        pil_image = self.plugin_dict["image"]
        pil_image.thumbnail((250, 90))
        self.image.set_pixbuf(image2pixbuf(pil_image, force_transparency=True))
        self.main_button_box.append(self.image)

        self.label_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL,
                                 margin_start=6, margin_top=6)
        self.main_button_box.append(self.label_box)

        self.name_label = Gtk.Label(label=self.plugin_dict["name"],
                                    css_classes=["bold"],
                                    xalign=0)
        self.label_box.append(self.name_label)

        self.author_label = Gtk.Label(label=f"By {self.plugin_dict['user_name']}",
                                      sensitive=False, #Grey out
                                      xalign=0)
        self.label_box.append(self.author_label)

        self.batch_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL,
                                 hexpand=False, vexpand=False,
                                 margin_start=7, margin_top=15, margin_bottom=15)
        # self.overlay.add_overlay(self.batch_box)
        self.main_button_box.append(self.batch_box)

        if self.plugin_dict["official"]:
            self.batch_box.append(OfficialBatch(margin_end=7))
        
        if self.plugin_dict["commit_sha"] is not None:
            self.batch_box.append(VerifiedBatch())

        self.main_button_box.append(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL))

        self.button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL,
                                  hexpand=True)
        self.main_box.append(self.button_box)

        self.github_button = Gtk.Button(icon_name="github-symbolic",
                                        hexpand=True,
                                        css_classes=["no-round-top-left", "no-round-top-right", "no-round-bottom-right"])
        self.github_button.connect("clicked", self.on_github_clicked)
        self.button_box.append(self.github_button)

        self.button_box.append(Gtk.Separator(orientation=Gtk.Orientation.VERTICAL))

        self.download_button = Gtk.Button(icon_name="download-symbolic",
                                          hexpand=True,
                                          css_classes=["no-round-top-left", "no-round-top-right", "no-round-bottom-left"])
        self.download_button.connect("clicked", self.on_download_clicked)
        self.button_box.append(self.download_button)


    def on_github_clicked(self, button: Gtk.Button):
        web.open(self.plugin_dict["url"])

    def on_download_clicked(self, button: Gtk.Button):
        self.install()

    def install(self):
        asyncio.run(self.plugin_page.store.backend.install_plugin(plugin_dict=self.plugin_dict))