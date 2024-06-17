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

from src.windows.Store.StoreData import PluginData

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, GLib, Gio, Gdk, GObject, GdkPixbuf

# Import python modules
import webbrowser as web
import asyncio
import threading
from packaging import version
from loguru import logger as log

# Import own modules
from src.windows.Store.StorePage import StorePage
from src.windows.Store.Badges import OfficialBadge, VerifiedBadge
from src.backend.DeckManagement.ImageHelpers import image2pixbuf
from src.backend.DeckManagement.HelperMethods import is_video
from src.windows.Store.Preview import StorePreview
from src.backend.Store.StoreBackend import NoConnectionError

# Typing
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.windows.Store.Store import Store

# Import globals
import globals as gl


class PluginPage(StorePage):
    def __init__(self, store: "Store"):
        super().__init__(store=store)
        self.store = store
        self.compatible_section.search_entry.set_placeholder_text(gl.lm.get("store.plugins.search-placeholder"))
        self.incompatible_section.search_entry.set_placeholder_text(gl.lm.get("store.plugins.search-placeholder"))

        threading.Thread(target=self.load, name="load_plugin_page").start()

    @log.catch
    def load(self):
        self.set_loading()
        plugins: list[PluginData] = self.store.backend.get_all_plugins()
        if isinstance(plugins, NoConnectionError):
            self.show_connection_error()
            return
        for plugin in plugins:
            if plugin.is_compatible:
                section = self.compatible_section
            else:
                section = self.incompatible_section
            GLib.idle_add(section.append_child, PluginPreview(plugin_page=self, plugin_data=plugin))

        self.set_loaded()

    def check_required_version(self, app_version_to_check: str, is_min_app_version: bool = False):
        if is_min_app_version:
            if app_version_to_check is None:
                return True
            min_version = version.parse(app_version_to_check)
            app_version = version.parse(gl.app_version)

            return min_version < app_version


class PluginPreview(StorePreview):
    def __init__(self, plugin_page: PluginPage, plugin_data: PluginData):
        super().__init__(store_page=plugin_page)
        self.plugin_page = plugin_page
        self.plugin_data = plugin_data

        self.set_author_label(plugin_data.author)
        self.set_name_label(plugin_data.plugin_name)
        self.set_image(plugin_data.image)
        self.set_url(plugin_data.github)

        self.set_official(plugin_data.official)
        self.set_verified(plugin_data.verified)

        # Set install button state
        if plugin_data.local_sha is None:
            self.set_install_state(0)
        elif plugin_data.local_sha == plugin_data.commit_sha:
            self.set_install_state(1)
        else:
            self.set_install_state(2)

        description = self.plugin_data.short_description
        if description in ["", "N/A", None]:
            description = self.plugin_data.description
        self.set_description(description)

    def install(self):
        asyncio.run(self.store.backend.install_plugin(plugin_data=self.plugin_data))
        self.set_install_state(1)

    def uninstall(self):
        self.store.backend.uninstall_plugin(plugin_id=self.plugin_data.plugin_id)
        self.set_install_state(0)

    def update(self):
        self.store.backend.uninstall_plugin(plugin_id=self.plugin_data.plugin_id, remove_from_pages=False,
                                            remove_files=False)
        self.install()

    def on_click_main(self, button: Gtk.Button):
        self.plugin_page.set_info_visible(True)

        # Update info page
        self.plugin_page.info_page.set_name(self.plugin_data.plugin_name)
        self.plugin_page.info_page.set_description(gl.lm.get_custom_translation(self.plugin_data.descriptions))
        self.plugin_page.info_page.set_author(self.plugin_data.author)
        self.plugin_page.info_page.set_version(self.plugin_data.plugin_version)

        self.plugin_page.info_page.set_license(self.plugin_data.license)
        self.plugin_page.info_page.set_copyright(self.plugin_data.copyright)
        self.plugin_page.info_page.set_original_url(self.plugin_data.original_url)
        self.plugin_page.info_page.set_license_description(gl.lm.get_custom_translation(self.plugin_data.license_descriptions))

    def check_required_version(self, app_version_to_check: str):
        if app_version_to_check is None:
            return True
        min_version = version.parse(app_version_to_check)
        app_version = version.parse(gl.app_version)

        return min_version < app_version
