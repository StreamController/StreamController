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
import os
import shutil
from loguru import logger as log

# Import own modules
from src.windows.Store.StorePage import StorePage
from src.windows.Store.Badges import OfficialBadge, VerifiedBadge
from src.backend.DeckManagement.ImageHelpers import image2pixbuf
from src.backend.DeckManagement.HelperMethods import is_video
from src.windows.Store.Preview import StorePreview
from src.windows.Store.StoreBackend import NoConnectionError

# Typing
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from src.windows.Store.Store import Store

# Import globals
import globals as gl


class IconPage(StorePage):
    def __init__(self, store: "Store"):
        super().__init__(store=store)
        self.store = store
        self.search_entry.set_placeholder_text(gl.lm.get("store.icons.search-placeholder"))

        threading.Thread(target=self.load, name="load_icon_page").start()

    def load(self):
        self.set_loading()
        icons = asyncio.run(self.store.backend.get_all_icons())
        if isinstance(icons, NoConnectionError):
            self.show_connection_error()
            return
        for icon in icons:
            GLib.idle_add(self.flow_box.append, IconPreview(icon_page=self, icon_dict=icon))

        self.set_loaded()


class IconPreview(StorePreview):
    def __init__(self, icon_page:IconPage, icon_dict:dict):
        super().__init__(store_page=icon_page)
        self.icon_dict = icon_dict
        self.icon_page = icon_page

        self.set_author_label(icon_dict["user_name"])
        self.set_name_label(icon_dict["name"])
        self.set_image(icon_dict["image"])
        self.set_url(icon_dict["url"])

        self.set_official(icon_dict["official"])
        self.set_verified(icon_dict["commit_sha"] is not None)

        if icon_dict["local_sha"] is None:
            self.set_install_state(0)
        elif icon_dict["commit_sha"] == icon_dict["local_sha"]:
            self.set_install_state(1)
        else:
            self.set_install_state(2)

    def install(self):
        folder_name = f"{self.icon_dict['user_name']}::{self.icon_dict['name']}"
        if os.path.exists(os.path.join(gl.DATA_PATH, "icons", folder_name)):
            shutil.rmtree(os.path.join(gl.DATA_PATH, "icons", folder_name))
        if not os.path.exists(os.path.join(gl.DATA_PATH, "icons")):
            os.mkdir(os.path.join(gl.DATA_PATH, "icons"))

        asyncio.run(self.store.backend.clone_repo(
            repo_url=self.icon_dict["url"],
            local_path=os.path.join(gl.DATA_PATH, "icons", folder_name),
            commit_sha=self.icon_dict["commit_sha"]
        ))
        self.set_install_state(1)

    def uninstall(self):
        folder_name = f"{self.icon_dict['user_name']}::{self.icon_dict['name']}"
        if os.path.exists(os.path.join(gl.DATA_PATH, "icons", folder_name)):
            os.remove(os.path.join(gl.DATA_PATH, "icons", folder_name))
        self.set_install_state(0)

    def update(self):
        self.install()

    def on_click_main(self, button: Gtk.Button):
        self.icon_page.set_info_visible(True)

        # Update info page
        self.icon_page.info_page.set_name(self.icon_dict.get("name"))
        self.icon_page.info_page.set_description(self.icon_dict.get("description"))
        self.icon_page.info_page.set_author(self.icon_dict.get("user_name"))
        self.icon_page.info_page.set_version(self.icon_dict.get("version"))

        self.icon_page.info_page.set_license(self.icon_dict.get("license"))
        self.icon_page.info_page.set_copyright(self.icon_dict.get("copyright"))
        self.icon_page.info_page.set_original_url(self.icon_dict.get("original_url"))
        self.icon_page.info_page.set_license_description(self.icon_dict.get("license_description"))