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
from src.windows.Store.Preview import StorePreview

# Typing
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from src.windows.Store.Store import Store


class IconPage(StorePage):
    def __init__(self, store: "Store"):
        super().__init__(store=store)
        self.store = store
        self.search_entry.set_placeholder_text("Search for icons")

        threading.Thread(target=self.load).start()

    def load(self):
        self.set_loading()
        icons = asyncio.run(self.store.backend.get_all_icons())
        for icon in icons:
            GLib.idle_add(self.flow_box.append, IconPreview(icon_page=self, icon_dict=icon))

        self.set_loaded()


class IconPreview(StorePreview):
    def __init__(self, icon_page:IconPage, icon_dict:dict):
        super().__init__(store_page=icon_page)
        self.plugin_dict = icon_dict

        self.set_author_label(icon_dict["user_name"])
        self.set_name_label(icon_dict["name"])
        self.set_image(icon_dict["image"])
        self.set_url(icon_dict["url"])

        # self.set_official(icon_dict["official"])
        # self.set_verified(icon_dict["commit_sha"] is not None)

    def install(self):
        pass

    def uninstall(self):
        pass