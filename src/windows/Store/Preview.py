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
from PIL import Image
import webbrowser as web
import asyncio

# Import own modules
from src.windows.Store.StorePage import StorePage
from src.backend.DeckManagement.ImageHelpers import image2pixbuf
from src.windows.Store.Batches import OfficialBatch, VerifiedBatch

class StorePreview(Gtk.FlowBoxChild):
    def __init__(self, store_page: StorePage):
        super().__init__()
        self.store_page = store_page
        self.store = store_page.store

        self.url = None

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
        self.main_button.connect("clicked", self.on_click_main)
        self.main_box.append(self.main_button)
        
        self.main_button_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL,
                                       hexpand=True, vexpand=False)
        self.main_button.set_child(self.main_button_box)
        
        self.image = Gtk.Picture(hexpand=True,
                                 content_fit=Gtk.ContentFit.COVER,
                                 height_request=90, width_request=250,
                                 css_classes=["plugin-store-image"])
        self.main_button_box.append(self.image)

        self.label_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL,
                                 margin_start=6, margin_top=6)
        self.main_button_box.append(self.label_box)

        self.name_label = Gtk.Label(css_classes=["bold"],
                                    xalign=0)
        self.label_box.append(self.name_label)

        self.author_label = Gtk.Label(sensitive=False, #Grey out
                                      xalign=0)
        self.label_box.append(self.author_label)

        self.batch_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL,
                                 hexpand=False, vexpand=True,
                                 margin_start=7, margin_top=15, margin_bottom=15)
        # self.overlay.add_overlay(self.batch_box)
        self.main_button_box.append(self.batch_box)

        self.official_batch = OfficialBatch(margin_end=7, visible=False)
        self.verified_batch = VerifiedBatch(visible=False)

        self.batch_box.append(self.official_batch)
        self.batch_box.append(self.verified_batch)

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

        self.remove_button = Gtk.Button(icon_name="remove-symbolic",
                                        hexpand=True,
                                        css_classes=["no-round-top-left", "no-round-top-right", "no-round-bottom-right"])
        self.remove_button.connect("clicked", self.on_remove_clicked)
        self.button_box.append(self.remove_button)

    def set_image(self, image:Image):
        image.thumbnail((250, 90))
        pixbuf = image2pixbuf(image, force_transparency=True)
        GLib.idle_add(self.image.set_pixbuf, pixbuf)

    def set_official(self, official:bool):
        self.official_batch.set_visible(official)

    def set_verified(self, verified:bool):
        self.verified_batch.set_visible(verified)

    def set_author_label(self, author:str):
        self.author_label.set_text(author)

    def set_name_label(self, name:str):
        self.name_label.set_text(name)

    def set_url(self, url:str):
        self.url = url

    def on_github_clicked(self, button: Gtk.Button):
        if self.url is None:
            return
        web.open(self.url)

    def on_download_clicked(self, button: Gtk.Button):
        self.install()

    def install(self):
        pass

    def on_remove_clicked(self, button: Gtk.Button):
        self.uninstall()

    def uninstall(self):
        pass

    def on_click_main(self, button: Gtk.Button):
        pass