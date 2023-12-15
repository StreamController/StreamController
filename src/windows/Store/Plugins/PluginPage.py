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
from src.windows.Store.Backend import NoConnectionError

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
        if isinstance(plugins, NoConnectionError):
            self.show_connection_error()
            return
        for plugin in plugins:
            GLib.idle_add(self.flow_box.append, PluginPreview(plugin_page=self, plugin_dict=plugin))

        self.set_loaded()


class PluginPreview(StorePreview):
    def __init__(self, plugin_page:PluginPage, plugin_dict:dict):
        super().__init__(store_page=plugin_page)
        self.plugin_dict = plugin_dict

        self.set_author_label(plugin_dict["user_name"])
        self.set_name_label(plugin_dict["name"])
        self.set_image(plugin_dict["image"])
        self.set_url(plugin_dict["url"])

        self.set_official(plugin_dict["official"])
        self.set_verified(plugin_dict["commit_sha"] is not None)

        # Set install button state
        if plugin_dict["local-sha"] is None:
            self.set_install_state(0)
        elif plugin_dict["local-sha"] == plugin_dict["commit_sha"]:
            self.set_install_state(1)
        else:
            self.set_install_state(2)

    def install(self):
        asyncio.run(self.store.backend.install_plugin(plugin_dict=self.plugin_dict))
        self.set_install_state(1)

    def uninstall(self):
        self.store.backend.uninstall_plugin(plugin_id=self.plugin_dict["id"])
        self.set_install_state(0)

    def update(self):
        self.install()