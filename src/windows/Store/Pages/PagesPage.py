"""
Author: Core447
Year: 2026

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

from src.windows.Store.StoreData import PageData

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, GLib

# Import python modules
import asyncio
import os
import threading
from loguru import logger as log

# Import own modules
from src.windows.Store.StorePage import StorePage
from src.windows.Store.Preview import StorePreview
from src.windows.PageManager.Importer.Importer import Importer
from src.backend.PageManagement import StorePages
from src.backend.DeckManagement.HelperMethods import recursive_hasattr
from src.backend.Store.StoreBackend import NoConnectionError

# Import signals
from src.Signals import Signals

# Typing
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from src.windows.Store.Store import Store

# Import globals
import globals as gl


class PagesPage(StorePage):
    def __init__(self, store: "Store"):
        super().__init__(store=store)
        self.store = store
        self.compatible_section.search_entry.set_placeholder_text(gl.lm.get("store.pages.search-placeholder"))
        self.incompatible_section.search_entry.set_placeholder_text(gl.lm.get("store.pages.search-placeholder"))

        threading.Thread(target=self.load, name="load_pages_page").start()

    @log.catch
    def load(self):
        self.set_loading()
        pages: list[PageData] = asyncio.run(self.store.backend.get_all_pages())
        if isinstance(pages, NoConnectionError):
            self.show_connection_error()
            return
        for page in pages:
            if page.is_compatible:
                section = self.compatible_section
            else:
                section = self.incompatible_section
            GLib.idle_add(section.append_child, PagePreview(pages_page=self, page_data=page))

        self.set_loaded()


class PagePreview(StorePreview):
    def __init__(self, pages_page: PagesPage, page_data: PageData):
        super().__init__(store_page=pages_page)
        self.page_data = page_data
        self.pages_page = pages_page

        self.set_author_label(page_data.author)
        self.set_name_label(page_data.page_name)
        self.set_image(page_data.image)
        self.set_url(page_data.github)

        self.set_official(page_data.official)
        self.set_verified(page_data.verified)

        self.warning_badge.set_tooltip("store.badges.page.warning")
        self.official_badge.set_tooltip("store.badges.page.official")
        self.verified_badge.set_tooltip("store.badges.page.verified")

        self.update_install_state()

        description = self.page_data.short_description
        if description in ["", "N/A", None]:
            description = self.page_data.description
        self.set_description(description)

    def update_install_state(self):
        if self.page_data.local_sha is None:
            GLib.idle_add(self.set_install_state, 0)
        elif self.page_data.local_sha == self.page_data.commit_sha:
            GLib.idle_add(self.set_install_state, 1)
        else:
            GLib.idle_add(self.set_install_state, 2)

    ## Install

    def install(self):
        bundle_path = asyncio.run(self.store.backend.download_page(page_data=self.page_data))
        if bundle_path is None:
            return

        page_name = self.get_target_page_name()

        if not self.run_importer(bundle_path, page_name):
            # The user cancelled or the import failed
            return

        # Same path the importer writes the page to
        page_path = os.path.join(gl.DATA_PATH, "pages", f"{page_name}.json")
        if not os.path.isfile(page_path):
            log.error(f"Page {page_name} is missing after the import")
            return

        StorePages.set_store_origin(
            page_path=page_path,
            page_id=self.page_data.page_id,
            url=self.page_data.github,
            path=self.page_data.page_path,
            commit=self.page_data.commit_sha
        )

        self.page_data.local_sha = self.page_data.commit_sha
        self.update_install_state()

    def get_target_page_name(self) -> str:
        """
        Updating replaces the page it was installed as, installing never overwrites
        a page the user already has.
        """
        installed_path = StorePages.find_installed_page(self.page_data.page_id)
        if installed_path is not None:
            return os.path.splitext(os.path.basename(installed_path))[0]

        name = self.page_data.page_name or self.page_data.repository_name or "Page"
        return StorePages.unique_page_name(name)

    def run_importer(self, bundle_path: str, page_name: str) -> bool:
        """
        Hands the bundle to the normal page importer, which asks about missing plugins
        and packs, downloads them and imports the assets that came with the page.
        Blocks the calling (install) thread until the import is done.
        """
        finished = threading.Event()
        result: dict[str, bool] = {}

        def on_finished():
            result["imported"] = True
            finished.set()

        def on_window_closed(*args):
            # Never leave the install thread waiting for a window that is gone
            finished.set()
            return False

        def show():
            importer = Importer(gl.app, self.store)
            importer.connect("close-request", on_window_closed)
            importer.present()
            importer.import_pages(bundle_path, "streamcontroller", on_finished=on_finished, rename_to=page_name)

        GLib.idle_add(show)
        finished.wait()

        return result.get("imported", False)

    ## Uninstall

    def uninstall(self):
        page_path = StorePages.find_installed_page(self.page_data.page_id)
        if page_path is None:
            self.page_data.local_sha = None
            self.update_install_state()
            return

        page_name = os.path.splitext(os.path.basename(page_path))[0]

        if len(gl.page_manager.get_pages(add_custom_pages=False)) <= 1:
            self.show_message(gl.lm.get("store.pages.cant-uninstall-last.title"),
                              gl.lm.get("store.pages.cant-uninstall-last.body"))
            return

        if not self.ask(gl.lm.get("store.pages.uninstall-confirm.title"),
                        f'{gl.lm.get("store.pages.uninstall-confirm.body")} "{page_name}"?',
                        gl.lm.get("store.pages.uninstall-confirm.confirm"),
                        destructive=True):
            return

        gl.page_manager.remove_page(page_path)
        gl.signal_manager.trigger_signal(Signals.PageDelete, page_path)
        self.reload_page_selectors()

        self.page_data.local_sha = None
        self.update_install_state()

    ## Update

    def update(self):
        if not self.ask(gl.lm.get("store.pages.update-confirm.title"),
                        gl.lm.get("store.pages.update-confirm.body"),
                        gl.lm.get("store.pages.update-confirm.confirm")):
            return

        self.install()

    ## Helpers

    def reload_page_selectors(self):
        if recursive_hasattr(gl, "app.main_win.sidebar.page_selector"):
            GLib.idle_add(gl.app.main_win.sidebar.page_selector.update)
        if recursive_hasattr(gl, "page_manager_window.page_selector"):
            GLib.idle_add(gl.page_manager_window.page_selector.load_pages)

    def ask(self, title: str, body: str, confirm_label: str, destructive: bool = False) -> bool:
        """Asks the user for confirmation. Blocks the calling thread until answered."""
        answer: dict[str, str] = {}
        answered = threading.Event()

        def show():
            dialog = Adw.MessageDialog(transient_for=self.store, modal=True, heading=title, body=body)
            dialog.add_response("cancel", gl.lm.get("store.pages.confirm.cancel"))
            dialog.add_response("confirm", confirm_label)
            dialog.set_default_response("cancel")
            dialog.set_close_response("cancel")
            dialog.set_response_appearance("confirm", Adw.ResponseAppearance.DESTRUCTIVE if destructive
                                           else Adw.ResponseAppearance.SUGGESTED)

            def on_response(dialog, response):
                answer["response"] = response
                answered.set()
                dialog.destroy()

            dialog.connect("response", on_response)
            dialog.present()

        GLib.idle_add(show)
        answered.wait()

        return answer.get("response") == "confirm"

    def show_message(self, title: str, body: str):
        def show():
            dialog = Adw.MessageDialog(transient_for=self.store, modal=True, heading=title, body=body)
            dialog.add_response("ok", gl.lm.get("store.pages.confirm.ok"))
            dialog.connect("response", lambda dialog, response: dialog.destroy())
            dialog.present()

        GLib.idle_add(show)

    def on_click_main(self, button: Gtk.Button):
        self.pages_page.set_info_visible(True)

        # Update info page
        self.pages_page.info_page.set_name(self.page_data.page_name)
        self.pages_page.info_page.set_description(self.page_data.description)
        self.pages_page.info_page.set_author(self.page_data.author)
        self.pages_page.info_page.set_version(self.page_data.page_version)
        self.pages_page.info_page.set_deck_info(self.page_data.deck)

        self.pages_page.info_page.set_license(self.page_data.license)
        self.pages_page.info_page.set_copyright(self.page_data.copyright)
        self.pages_page.info_page.set_original_url(self.page_data.original_url)
        self.pages_page.info_page.set_license_description(gl.lm.get_custom_translation(self.page_data.license_descriptions))
        self.pages_page.info_page.clear_plugin_data()
