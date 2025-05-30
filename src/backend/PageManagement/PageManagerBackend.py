"""
Author: Core447
Year: 2023

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
any later version.

This programm comes with ABSOLUTELY NO WARRANTY!

You should have received a copy of the GNU General Public License
along with this program. If not, see <https://www.gnu.org/licenses/>.
"""
import dataclasses
# Import Python modules
import datetime
import gc
import os
import shutil
import json
from copy import copy
from signal import Signals
import time
from loguru import logger as log

from src.Signals import Signals

# Import own modules
from src.backend.PageManagement.Page import Page
from src.backend.PageManagement.DummyPage import DummyPage
from src.backend.DeckManagement.HelperMethods import get_sub_folders, natural_sort, natural_sort_by_filenames, recursive_hasattr, sort_times

# Import globals
import globals as gl

class PageManagerBackendV2:
    def __init__(self, settings_manager):
        self.settings_manager = settings_manager

        self.pages = {}
        self.custom_pages = []

        self.page_order = []

        self.max_pages = 3
        self.page_number = 0

        self.PAGE_PATH = os.path.join(gl.DATA_PATH, "pages")
        self.PAGE_SETTINGS_PATH = os.path.join(gl.DATA_PATH, "settings", "pages.json")

    def load_page(self, path: str, deck_controller: "DeckController") -> Page:
        """
        This loads the page into the page dict and increases the current page number.
        :param path: The path to the page
        :param deck_controller: The deck controller instance that the page belongs to
        :return: The newly created page object
        """
        if not path or not os.path.isfile(path):
            return None

        page = Page(json_path=path, deck_controller=deck_controller)
        self.pages.setdefault(deck_controller, {})
        self.pages[deck_controller][path] = {"page": page, "page_number": self.page_number}
        self.page_number += 1

        return page

    def get_page(self, path: str, deck_controller: "DeckController") -> Page:
        page = self.pages.get(deck_controller, {}).get(path, {})

        if not page:
            page_object = self.load_page(path, deck_controller)
            #self.clear_old_cached_pages()
        else:
            page["page_number"] = self.page_number
            page_object = page["page"]
            self.page_number += 1

        return page_object

    def get_pages(self, add_custom_pages: bool = True, sort: bool = True) -> list[str]:
        pages = []

        os.makedirs(self.PAGE_PATH, exist_ok=True)

        for page in os.listdir(self.PAGE_PATH):
            if not page.endswith(".json"):
                continue

            pages.append(os.path.join(self.PAGE_PATH, page))

        if add_custom_pages:
            pages.extend(self.custom_pages)

        if sort:
            pages = natural_sort_by_filenames(pages)

        return pages

    def get_page_names(self, add_custom_pages: bool = True) -> list[str]:
        page_names = []

        for page in self.get_pages(add_custom_pages=add_custom_pages):
            name = os.path.basename(page)
            name = name.split(".")[0]
            page_names.append(name)

        return page_names

    def clear_old_cached_pages(self):
        pages = sum(len(controller) for controller in self.pages.values())

        for i in range(pages - self.max_pages):
            lowest_page = min(
                page_data["page_number"]
                for controller_pages in self.pages.values()
                for page_data in controller_pages.values()
            )

            for controller, controller_pages in self.pages.items():
                for path, page_data in controller_pages.items():
                    if controller.active_page is None:
                        continue

                    page_obj = page_data["page"]

                    if not page_obj.ready_to_clear:
                        continue

                    if page_obj is controller.active_page:
                        continue

                    if page_data["page_number"] != lowest_page:
                        continue

                    page_obj.clear_action_objects()
                    del controller_pages[path]
                    break

    def get_default_page(self, deck_serial_number: str):
        page_settings = self.settings_manager.load_settings_from_file(self.PAGE_SETTINGS_PATH)
        page_path = page_settings.get("default-pages", {}).get(deck_serial_number, None)

        if page_path and os.path.isfile(page_path):
            return page_path

        return None

    def set_default_page(self, deck_serial_number: str, path: str):
        page_settings = self.settings_manager.load_settings_from_file(self.PAGE_SETTINGS_PATH)
        page_settings.setdefault("default-pages", {})
        page_settings["default-pages"][deck_serial_number] = path
        self.settings_manager.save_settings_to_file(self.PAGE_SETTINGS_PATH, page_settings)

    def get_all_default_page_serial_numbers(self) -> list[str]:
        serial_numbers = []

        page_settings = self.settings_manager.load_settings_from_file(self.PAGE_SETTINGS_PATH)
        for serial_number, page_path in page_settings.get("default-pages", {}).items():
            if not page_path:
                continue
            serial_numbers.append(serial_number)

        return serial_numbers

    def get_serial_numbers_from_page(self, path: str) -> list[str]:
        serial_numbers = []

        page_settings = self.settings_manager.load_settings_from_file(self.PAGE_SETTINGS_PATH)
        for serial_number, page_path in page_settings.get("default-pages", {}).items():
            if path != page_path:
                continue
            serial_numbers.append(serial_number)

        return serial_numbers

    def set_pages_to_cache(self, amount: int):
        old_max_pages = self.max_pages

        self.max_pages = amount + 1

        if old_max_pages > self.max_pages:
            self.clear_old_cached_pages()

    def move_page(self, old_path: str, new_path: str):
        shutil.copy2(old_path, new_path)

        page_settings = gl.settings_manager.load_settings_from_file(self.PAGE_SETTINGS_PATH)
        default_pages = page_settings.get("default-pages", {})

        # Update Path in Objects
        for controller in gl.deck_manager.deck_controller:
            if controller.active_page is None:
                continue

            page = self.get_page(old_path, controller)

            if not page:
                continue

            page.json_path = new_path

        # Update path in Settings file
        for serial_number, path in default_pages.items():
            if path != old_path:
                continue
            default_pages[serial_number] = new_path

        # Save updated default pages
        page_settings["default-pages"] = default_pages
        gl.settings_manager.save_settings_to_file(self.PAGE_SETTINGS_PATH, page_settings)

        os.remove(old_path)
        #self.update_auto_change_info()

    def remove_page(self, page_path: str):
        settings_path = os.path.join(gl.DATA_PATH, "settings", "pages.json")
        settings = gl.settings_manager.load_settings_from_file(settings_path)
        default_pages = settings.get("default-pages", {})

        # Iterate over all deck controllers to handle any that are using the page to be removed
        for controller in gl.deck_manager.deck_controller:
            active_page = controller.active_page

            # Skip controllers without an active page or not using the page to be deleted
            if not active_page or active_page.json_path != page_path:
                continue

            # Determine the default page for this controller's deck
            serial = controller.deck.get_serial_number()
            deck_default = self.get_default_page(serial)

            if deck_default and deck_default != page_path:
                # Load and switch to the default page if it's not the one being deleted
                new_page = self.get_page(deck_default, controller)
            else:
                # Fallback: load the first available page if default is being deleted
                page_list = self.get_pages()
                if page_path in page_list:
                    page_list.remove(page_path)
                new_page = self.get_page(page_list[0], controller) if page_list else None

            if new_page:
                controller.load_page(new_page)

            # Remove the page from the created pages cache for this controller
            controller_pages = self.pages.get(controller, {})
            if page_path in controller_pages:
                page_obj = controller_pages[page_path]["page"]
                page_obj.clear_action_objects()
                del controller_pages[page_path]

                # Remove the controller entry entirely if it no longer has cached pages
                if not controller_pages:
                    del self.pages[controller]

        # Delete the JSON file representing the page
        if os.path.exists(page_path):
            os.remove(page_path)

        # Remove any references to this page in the default-pages setting
        new_default_pages = {}
        for serial, path in default_pages.items():
            if path != page_path:
                new_default_pages[serial] = path

        settings["default-pages"] = new_default_pages
        gl.settings_manager.save_settings_to_file(settings_path, settings)

        #self.update_auto_change_info()

    def add_page(self, page_name: str, page_dict: dict = None):
        page_dict = page_dict or {}

        with open(os.path.join(self.PAGE_PATH, f"{page_name}.json"), "w") as f:
            json.dump(page_dict, f)

        #self.update_auto_change_info()

class PageManagerBackend:
    def __init__(self, settings_manager):
        self.v2 = PageManagerBackendV2(settings_manager)


        self.settings_manager = settings_manager
        self.global_settings_manager = gl.settings_manager

        self.created_pages = {}
        self.created_pages_order = []

        self.max_pages = 3

        settings = self.global_settings_manager.get_app_settings()
        self.set_n_pages_to_cache(int(settings.get("performance", {}).get("n-cached-pages", self.max_pages)))

        self.page_number: int = 0

        self.custom_pages = []

        self.auto_change_info = {}
        self.update_auto_change_info()

        self.dummy_page = DummyPage()

    def set_n_pages_to_cache(self, n_pages):
        self.v2.set_pages_to_cache(n_pages)

        #old_max_pages = self.max_pages
        #self.max_pages = n_pages + 1 # +1 to keep the active page

        #if old_max_pages > self.max_pages:
        #    self.clear_old_cached_pages()

    def save_pages(self) -> None:
        for page in self.pages.values():
            page.save()

    def get_pages(self, add_custom_pages: bool = True, sort: bool = True) -> list[str]:
        return self.v2.get_pages(add_custom_pages=add_custom_pages, sort=sort)


        #pages = []
        ## Create pages dir if it doesn't exist
        #os.makedirs(os.path.join(gl.DATA_PATH, "pages"), exist_ok=True)
        ## Get all pages
        #for page in os.listdir(os.path.join(gl.DATA_PATH, "pages")):
        #    if os.path.splitext(page)[1] == ".json":
        #        pages.append(os.path.join(gl.DATA_PATH, "pages", page))

        #if add_custom_pages:
        #    pages.extend(self.custom_pages)

        #if sort:
        #    pages = natural_sort_by_filenames(pages)

        ## print(pages)
        #return pages

    def get_page_names(self, add_custom_pages: bool = True) -> list[str]:
        return self.v2.get_page_names(add_custom_pages=add_custom_pages)

        #pages: list[str] = []
        #for page in self.get_pages(add_custom_pages):
        #    pages.append(os.path.splitext(os.path.basename(page))[0])
        #return pages
    
    def create_page(self, path: str, deck_controller: "DeckController") -> Page:
        return self.v2.load_page(path, deck_controller)

        #if path is None:
        #    return None
        #if not os.path.exists(path):
        #    return None
        #page = Page(json_path=path, deck_controller=deck_controller)
        #self.created_pages.setdefault(deck_controller, {})
        #self.created_pages[deck_controller][path] = {
        #    "page": page,
        #    "page_number": self.page_number
        #}
        #self.page_number += 1

        #return page
    
    def get_page(self, path: str, deck_controller: "DeckController") -> Page:
        return self.v2.get_page(path, deck_controller)

        #if deck_controller in self.created_pages:
        #    if path in self.created_pages[deck_controller]:
        #        self.created_pages[deck_controller][path]["page_number"] = self.page_number
        #        self.page_number += 1
        #        return self.created_pages[deck_controller][path]["page"]
        #
        #new_page = self.create_page(path, deck_controller)
        #self.clear_old_cached_pages()
        #return new_page

    def clear_old_cached_pages(self):
        self.v2.clear_old_cached_pages()

        #n_pages = 0
        #for controller in self.created_pages:
        #    for page in self.created_pages[controller]:
        #        n_pages += 1

        #for _ in range(n_pages - self.max_pages):
        #    if n_pages > self.max_pages:
        #        # Remove entry with lowest page number
        #        lowest_page = min(self.created_pages[controller][p]["page_number"] for controller in self.created_pages for p in self.created_pages[controller])
        #        for controller in self.created_pages:
        #            for page in self.created_pages[controller]:
        #                if controller.active_page is None:
        #                    continue
        #                if not self.created_pages[controller][page]["page"].ready_to_clear:
        #                    continue
        #                if self.created_pages[controller][page]["page"] is controller.active_page:
        #                    continue
        #                if self.created_pages[controller][page]["page_number"] == lowest_page:
        #                    page_object: Page = self.created_pages[controller][page]["page"]
        #                    page_object.clear_action_objects()

        #                    self.created_pages[controller][page] = None
        #                    del self.created_pages[controller][page]
        #
        #                    break

    def get_default_page_for_deck(self, serial_number: str) -> str:
        return self.v2.get_default_page(serial_number)

        #page_settings = self.settings_manager.load_settings_from_file(os.path.join(gl.DATA_PATH, "settings", "pages.json"))
        #page_path = page_settings.get("default-pages", {}).get(serial_number, None)
        #if page_path is not None:
        #    if not os.path.exists(page_path):
        #        return None
        #    return page_path
        #return None
    
    def set_default_page_for_deck(self, serial_number: str, path: str):
        self.v2.set_default_page(serial_number, path)

        #page_settings = self.settings_manager.load_settings_from_file(os.path.join(gl.DATA_PATH, "settings", "pages.json"))
        #page_settings.setdefault("default-pages", {})
        #page_settings["default-pages"][serial_number] = path
        #self.settings_manager.save_settings_to_file(os.path.join(gl.DATA_PATH, "settings", "pages.json"), page_settings)

    def get_all_deck_serial_numbers_with_set_default_page(self) -> list[str]:
        return self.v2.get_all_default_page_serial_numbers()

        #matches: list[str] = []
        #page_settings = self.settings_manager.load_settings_from_file(os.path.join(gl.DATA_PATH, "settings", "pages.json"))
        #for serial_number in page_settings.get("default-pages", {}):
        #    if page_settings["default-pages"][serial_number] not in ["", None]:
        #        matches.append(serial_number)

        #return matches
    
    def get_all_deck_serial_numbers_with_page_as_default(self, path: str) -> list[str]:
        return self.v2.get_serial_numbers_from_page(path)

        #matches: list[str] = []
        #page_settings = self.settings_manager.load_settings_from_file(os.path.join(gl.DATA_PATH, "settings", "pages.json"))
        #for serial_number in page_settings.get("default-pages", {}):
        #    if page_settings["default-pages"][serial_number] == path:
        #        matches.append(serial_number)

        #return matches
    
    def move_page(self, old_path: str, new_path: str):
        self.v2.move_page(old_path, new_path)

        ## Copy page json file
        #shutil.copy2(old_path, new_path)

        ## Change name in page objects
        #for controller in gl.deck_manager.deck_controller:
        #    if controller.active_page is None:
        #        continue
        #    page = self.get_page(path=old_path, deck_controller=controller)
        #    if page is None:
        #        continue
        #    page.json_path = new_path
        #
        #    # Update default page settings
        #    settings = gl.settings_manager.load_settings_from_file(os.path.join(gl.DATA_PATH, "settings", "pages.json"))
        #    if settings.get("default-pages") is None:
        #        continue
        #    for serial_number, path in settings.get("default-pages", {}).items():
        #        if path == old_path:
        #            settings["default-pages"][serial_number] = new_path
        #    gl.settings_manager.save_settings_to_file(os.path.join(gl.DATA_PATH, "settings", "pages.json"), settings)

        ## Remove old page
        #os.remove(old_path)

        ## Update ui
        ## self.update_ui()

        #self.update_auto_change_info()

    def remove_page(self, page_path: str):
        self.v2.remove_page(page_path)

        ## Clear page objects
        #for controller in gl.deck_manager.deck_controller:
        #    if controller.active_page is None:
        #        continue

        #    if controller.active_page.json_path != page_path:
        #        continue

        #    deck_default_page = self.get_default_page_for_deck(controller.deck.get_serial_number())
        #    if page_path != deck_default_page and deck_default_page is not None:
        #        new_page = self.get_page(deck_default_page, controller)
        #        controller.load_page(new_page)
        #        continue

        #    else:
        #        page_list = self.get_pages()
        #        page_list.remove(page_path)
        #        controller.load_page(self.get_page(page_list[0], controller))


        ## Remove page json file
        #os.remove(page_path)

        #self.remove_page_path_from_created_pages(page_path)

        ## Remove default page entries
        #settings = gl.settings_manager.load_settings_from_file(os.path.join(gl.DATA_PATH, "settings", "pages.json"))
        #for serial_number, path in list(settings.get("default-pages",{}).items()):
        #    if path == page_path:
        #        del settings["default-pages"][serial_number]
        #gl.settings_manager.save_settings_to_file(os.path.join(gl.DATA_PATH, "settings", "pages.json"), settings)

        ## Update ui
        ## self.update_ui()

        #self.update_auto_change_info()

    #def remove_page_path_from_created_pages(self, path: str):
    #    for controller in self.created_pages:
    #        if path in self.created_pages[controller]:
    #            page_object: Page = self.created_pages[controller][path]["page"]
    #            page_object.clear_action_objects()

    #            self.created_pages[controller][path] = None
    #            del self.created_pages[controller][path]


    def add_page(self, name:str, page_dict: dict = None):
        self.v2.add_page(name, page_dict)


        #with open(os.path.join(gl.DATA_PATH, "pages", f"{name}.json"), "w") as f:
        #    json.dump(page_dict, f)

        ## Update ui
        ## self.update_ui()

        #self.update_auto_change_info()

    def register_page(self, path: str):
        if not os.path.exists(path):
            log.error(f"Page {path} does not exist")
            return
        log.trace(f"Registering page: {path}")
        self.custom_pages.append(path)

        # Update ui
        # self.update_ui()
        gl.signal_manager.trigger_signal(Signals.PageAdd, path)

        self.update_auto_change_info()

    def unregister_page(self, path: str):
        self.custom_pages.remove(path)

        gl.signal_manager.trigger_signal(Signals.PageDelete, path)

    def get_pages_with_path(self, page_path: str) -> list[Page]:
        pages: list[Page] = []

        ## Add from controllers
        for controller in gl.deck_manager.deck_controller:
            if controller.active_page is None:
                continue
            if controller.active_page.json_path == page_path:
                pages.append(controller.active_page)

        ## Add from cache
        for controller in self.created_pages:
            if page_path in self.created_pages[controller]:
                page = self.created_pages[controller][page_path]["page"]
                if page not in pages:
                    pages.append(page)

        return pages
    
    def reload_pages_with_path(self, page_path: str) -> None:
        pages = self.get_pages_with_path(page_path)

        for page in pages:
            page.load()
            if page.deck_controller.active_page == page:
                page.deck_controller.load_page(page, allow_reload=True)

    def reload_all_pages(self) -> None:
        for controller in gl.deck_manager.deck_controller:
            controller.load_page(controller.active_page, allow_reload=True)

    def update_dict_of_pages_with_path(self, page_path: str) -> None:
        pages = self.get_pages_with_path(page_path)
        for page in pages:
            page.update_dict()

    def update_auto_change_info(self):
        start = time.time()
        self.auto_change_info = {}
        pages = self.get_pages(sort=False)
        for page in pages:
            abs_path = os.path.abspath(page)
            page_dict = self.get_page_json(abs_path)
            if page_dict is None:
                continue
            self.auto_change_info[abs_path] = page_dict.get("auto-change", {})

        log.info(f"Updated auto-change info in {time.time() - start} seconds")

    def set_auto_change_info_for_page(self, page_path: str, info: dict) -> None:
        abs_path = os.path.abspath(page_path)
        self.auto_change_info[abs_path] = info
        page = self.get_page_json(abs_path)

        page["auto-change"] = info

        with open(abs_path, "w") as f:
            json.dump(page, f, indent=4)

        self.update_dict_of_pages_with_path(abs_path)

    def get_auto_change_info_for_page(self, page_path: str) -> dict:
        abs_path = os.path.abspath(page_path)
        return self.auto_change_info.get(abs_path, {})
    
    def get_page_json(self, page_path: str) -> dict:
        """
        Loads and returns the json of the page.
        If the page is corrupt it will fallback to the backed up page.
        """
        if not os.path.exists(page_path):
            return
        
        try:
            with open(page_path, "r") as f:
                return json.load(f)
        except json.decoder.JSONDecodeError:
            pass
        

        backup_path = os.path.join(gl.DATA_PATH, "pages", "backups", os.path.basename(page_path))
        if not os.path.exists(backup_path):
            log.error(f"Invalid json in {page_path}, no backup exists, returning None")
            return
        
        log.error(f"Invalid json in {page_path}, falling back to backup")
        try:
            with open(backup_path, "r") as f:
                return json.load(f)
        except json.decoder.JSONDecodeError:
            return
        
    def remove_asset_from_all_pages(self, path: str):
        if path in ["", None]:
            raise ValueError("Invalid path")
        
        for page_path in self.get_pages():
            page_had_asset = False
            with open(page_path, "r") as f:
                page_dict = json.load(f)
                for key in page_dict.get("keys", {}):
                    for state in page_dict["keys"][key].get("states", {}):
                        dict_path = page_dict["keys"][key]["states"][state].get("media", {}).get("path")
                        if dict_path is None:
                            continue
                        if os.path.abspath(dict_path) == os.path.abspath(path):
                            page_had_asset = True
                            page_dict["keys"][key]["states"][state]["media"]["path"] = None

            if page_had_asset:
                with open(page_path, "w") as f:
                    json.dump(page_dict, f, indent=4)

                self.update_dict_of_pages_with_path(page_path)

                pages = self.get_pages_with_path(page_path)
                for page in pages:
                    if page.deck_controller.active_page == page:
                        page.deck_controller.load_page(page, allow_reload=True)

    def get_best_page_path_match_from_name(self, name: str) -> str:
        if name in ["", None]:
            return
        
        # Is a full path
        if os.path.isfile(name):
            return name
        
        # Not a full path
        for page in self.get_pages():
            if os.path.basename(page) == name:
                return page
            if os.path.splitext(os.path.basename(page))[0] == name:
                return page
            
        return
    
    def backup_pages(self) -> None:
        time_stamp = datetime.datetime.now().isoformat()
        folder = os.path.join(gl.DATA_PATH, "pages", "backups", time_stamp)
        if os.path.exists(folder):
            return
        os.makedirs(folder)

        for page in self.get_pages():
            backup_path = os.path.join(folder, os.path.basename(page))
            shutil.copy(page, backup_path)


    def remove_old_backups(self) -> None:
        n_backups_to_keep = 5

        backup_dir = os.path.join(gl.DATA_PATH, "pages", "backups")

        unsorted_backups = get_sub_folders(backup_dir)
        sorted_backups = sort_times(unsorted_backups)

        if len(sorted_backups) <= n_backups_to_keep:
            return
        
        for backup in sorted_backups[:-n_backups_to_keep]:
            shutil.rmtree(os.path.join(backup_dir, backup))
            log.info(f"Removed old page backups: {backup}")