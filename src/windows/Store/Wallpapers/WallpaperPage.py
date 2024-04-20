"""
Year: 2024

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
from gi.repository import Gtk, GLib

# Import python modules
import webbrowser as web
import asyncio
import threading
import os
import shutil
from loguru import logger as log
import asyncio

# Import own modules
from src.windows.Store.StorePage import StorePage
from src.windows.Store.Badges import OfficialBadge, VerifiedBadge
from src.backend.DeckManagement.ImageHelpers import image2pixbuf
from src.backend.DeckManagement.HelperMethods import is_video
from src.windows.Store.Preview import StorePreview
from src.windows.Store.StoreBackend import NoConnectionError

# Import globals
import globals as gl

# Typing
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from src.windows.Store.Store import Store

class WallpaperPage(StorePage):
    def __init__(self, store: "Store"):
        super().__init__(store=store)
        self.store = store
        self.search_entry.set_placeholder_text(gl.lm.get("store.wallpapers.search-placeholder"))

        threading.Thread(target=self.load, name="load_wallpaper_page").start()

    def load(self):
        self.set_loading()
        icons = asyncio.run(self.store.backend.get_all_wallpapers())
        if isinstance(icons, NoConnectionError):
            self.show_connection_error()
            return
        for icon in icons:
            GLib.idle_add(self.flow_box.append, WallpaperPreview(wallpaper_page=self, wallpaper_dict=icon))

        self.set_loaded()


class WallpaperPreview(StorePreview):
    def __init__(self, wallpaper_page:WallpaperPage, wallpaper_dict:dict):
        super().__init__(store_page=wallpaper_page)
        self.wallpaper_dict = wallpaper_dict
        self.wallpaper_page = wallpaper_page

        self.set_author_label(wallpaper_dict["user_name"])
        self.set_name_label(wallpaper_dict["name"])
        self.set_image(wallpaper_dict["image"])
        self.set_url(wallpaper_dict["url"])

        self.set_official(wallpaper_dict["official"])
        self.set_verified(wallpaper_dict["commit_sha"] is not None)

        if wallpaper_dict["local_sha"] is None:
            self.set_install_state(0)
        elif wallpaper_dict["commit_sha"] == wallpaper_dict["local_sha"]:
            self.set_install_state(1)
        else:
            self.set_install_state(2)

        description = self.wallpaper_dict.get("short_description")
        if description in ["", "N/A", None]:
            description = self.wallpaper_dict.get("description")
        self.set_description(description)

    def install(self):
        asyncio.run(self.store.backend.install_wallpaper(wallpaper_dict=self.wallpaper_dict))
        self.set_install_state(1)

    def uninstall(self):
        asyncio.run(self.store.backend.uninstall_wallpaper(wallpaper_dict=self.wallpaper_dict))
        self.set_install_state(0)

    def update(self):
        self.install()

    def on_click_main(self, button: Gtk.Button):
        self.wallpaper_page.set_info_visible(True)

        # Update info page
        self.wallpaper_page.info_page.set_name(self.wallpaper_dict.get("name"))
        self.wallpaper_page.info_page.set_description(self.wallpaper_dict.get("description"))
        self.wallpaper_page.info_page.set_author(self.wallpaper_dict.get("user_name"))
        self.wallpaper_page.info_page.set_version(self.wallpaper_dict.get("version"))

        self.wallpaper_page.info_page.set_license(self.wallpaper_dict.get("license"))
        self.wallpaper_page.info_page.set_copyright(self.wallpaper_dict.get("copyright"))
        self.wallpaper_page.info_page.set_original_url(self.wallpaper_dict.get("original_url"))
        self.wallpaper_page.info_page.set_license_description(self.wallpaper_dict.get("license_description"))