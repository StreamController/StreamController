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
import zipfile
from copy import copy
from signal import Signals
import time
from typing import Union

from loguru import logger as log

from src.Signals import Signals
from src.backend.DeckManagement.DeckController import DeckController

# Import own modules
from src.backend.PageManagement.Page import Page
from src.backend.PageManagement.DummyPage import DummyPage
from src.backend.DeckManagement.HelperMethods import get_sub_folders, natural_sort, natural_sort_by_filenames, recursive_hasattr, sort_times

# Import globals
import globals as gl

class PageManagerBackendV2:
    def __init__(self, settings_manager):
        self.settings_manager = settings_manager

        self.pages: dict["DeckController", dict[str, dict[str, Union["Page", int]]]] = {}
        self.custom_pages = []

        self.page_order = []

        self.max_pages = 3
        self.page_number = 0

        self.MAX_BACKUPS = 5
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

    def register_page(self, path: str):
        if not os.path.isfile(path):
            log.error(f"Page {path} does not exist")
            return

        log.trace(f"Registering page {path}")
        self.custom_pages.append(path)

        gl.signal_manager.trigger_signal(Signals.PageAdd, path)

        # self.update_auto_change_info()

    def unregister_page(self, path: str):
        if not self.custom_pages.__contains__(path):
            return

        self.custom_pages.remove(path)
        gl.signal_manager.trigger_signal(Signals.PageDelete, path)

    def get_pages_with_path(self, path: str):
        pages_set = set()

        for controller in gl.deck_manager.deck_controller:
            # Check active_page
            page = controller.active_page
            if page is not None and page.json_path == path:
                pages_set.add(page)

            # Check in page cache for the same controller
            if controller not in self.pages:
                continue

            path_dict = self.pages[controller]
            if path in path_dict:
                page = path_dict[path]["page"]
                pages_set.add(page)

        return list(pages_set)

    def reload_pages_with_path(self, path: str):
        pages = self.get_pages_with_path(path)

        for page in pages:
            page.load()

            if page.deck_controller.active_page != page:
                continue

            page.deck_controller.load_page(page, allow_relaod=True)

    @staticmethod
    def reload_all_pages() -> None:
        for controller in gl.deck_manager.deck_controller:
            controller.load_page(controller.active_page, allow_reload=True)

    def update_dict_of_pages_with_path(self, path: str) -> None:
        pages = self.get_pages_with_path(path)
        for page in pages:
            page.update_dict()

    def get_page_data(self, path: str) -> dict:
        backup_path = os.path.join(self.PAGE_PATH, "backups", os.path.basename(path))

        if not os.path.exists(path) and os.path.exists(backup_path):
            path = backup_path

        try:
            with open(path, "r") as f:
                return json.load(f)
        except json.decoder.JSONDecodeError:
            return {}

    def remove_asset_from_all_pages(self, path: str):
        # Validate input path; reject empty or None
        if not path:
            raise ValueError("Invalid path")

        # Compute absolute path once for comparison
        abs_target_path = os.path.abspath(path)

        # Iterate over all page files (paths)
        for page_path in self.get_pages():
            page_had_asset = False  # Flag to track if this page had the asset

            # Open and load JSON page data
            with open(page_path, "r") as f:
                page_dict = json.load(f)

            # Safely get keys dictionary from page data
            keys = page_dict.get("keys", {})

            # Iterate over each key and its data
            for key, key_data in keys.items():
                # Get all states for this key
                states = key_data.get("states", {})

                # Iterate through each state and its data
                for state, state_data in states.items():
                    # Get media dictionary from state data
                    media = state_data.get("media", {})
                    dict_path = media.get("path")

                    # If no media path defined, skip
                    if dict_path is None:
                        continue

                    # Compare absolute paths; if match, remove asset reference
                    if os.path.abspath(dict_path) == abs_target_path:
                        page_had_asset = True
                        state_data["media"]["path"] = None  # Remove the asset path

            # If any asset was removed, update page file and reload pages
            if page_had_asset:
                # Write updated page data back to file with pretty JSON
                with open(page_path, "w") as f:
                    json.dump(page_dict, f, indent=4)

                # Update internal cache or tracking dict with this page path
                self.update_dict_of_pages_with_path(page_path)

                # Reload any loaded Page objects corresponding to this file
                pages = self.get_pages_with_path(page_path)
                for page in pages:
                    # Reload the page if it is currently active on its controller
                    if page.deck_controller.active_page == page:
                        page.deck_controller.load_page(page, allow_reload=True)

    def find_matching_page_path(self, name: str) -> str:
        if not name:
            return None

        # If 'name' is already a valid full file path, return it directly
        if os.path.isfile(name):
            return name

        # Normalize the name for comparison
        target_name = name.lower()

        for page_path in self.get_pages():
            base = os.path.basename(page_path).lower()
            base_no_ext = os.path.splitext(base)[0]

            # Check exact filename or filename without extension
            if base == target_name or base_no_ext == target_name:
                return page_path

        return None

    def backup_pages(self) -> None:
        # Create a timestamp string safe for filenames
        time_stamp = datetime.datetime.now().strftime("%Y%m%dT%H%M%S")

        # Create backup zip file path
        backup_zip_path = os.path.join(self.PAGE_PATH, "backups", f"backup_{time_stamp}.zip")

        # Ensure backup directory exists
        os.makedirs(os.path.dirname(backup_zip_path), exist_ok=True)

        # Create a zip archive and add all page files
        with zipfile.ZipFile(backup_zip_path, mode="w", compression=zipfile.ZIP_DEFLATED) as backup_zip:
            for page_path in self.get_pages():
                # Add each file with only its basename (no folders inside zip)
                backup_zip.write(page_path, arcname=os.path.basename(page_path))

    def remove_old_backups(self) -> None:
        backup_dir = os.path.join(self.PAGE_PATH, "backups")

        # List all zip files in the backup directory
        backup_files = [file for file in os.listdir(backup_dir) if file.endswith(".zip")]

        # Sort backups by timestamp embedded in filename, descending (newest first)
        # Assuming filename format: backup_YYYYMMDDTHHMMSS.zip
        def extract_timestamp(filename: str) -> str:
            # Extract the timestamp part, e.g. "20250530T142530" from "backup_20250530T142530.zip"
            return filename.removeprefix("backup_").removesuffix(".zip")

        sorted_backups = sorted(backup_files, key=extract_timestamp, reverse=True)

        # If backups are fewer than or equal to keep count, no deletion needed
        if len(sorted_backups) < self.MAX_BACKUPS:
            return

        # Delete oldest backups beyond the number to keep
        for old_backup in sorted_backups[self.MAX_BACKUPS-1:]:
            backup_path = os.path.join(backup_dir, old_backup)
            try:
                os.remove(backup_path)
                log.info(f"Removed old page backup file: {old_backup}")
            except Exception as e:
                log.error(f"Failed to remove backup file {old_backup}: {e}")


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

    def get_pages(self, add_custom_pages: bool = True, sort: bool = True) -> list[str]:
        return self.v2.get_pages(add_custom_pages=add_custom_pages, sort=sort)

    def get_page_names(self, add_custom_pages: bool = True) -> list[str]:
        return self.v2.get_page_names(add_custom_pages=add_custom_pages)
    
    def create_page(self, path: str, deck_controller: "DeckController") -> Page:
        return self.v2.load_page(path, deck_controller)
    
    def get_page(self, path: str, deck_controller: "DeckController") -> Page:
        return self.v2.get_page(path, deck_controller)

    def clear_old_cached_pages(self):
        self.v2.clear_old_cached_pages()

    def get_default_page_for_deck(self, serial_number: str) -> str:
        return self.v2.get_default_page(serial_number)
    
    def set_default_page_for_deck(self, serial_number: str, path: str):
        self.v2.set_default_page(serial_number, path)

    def get_all_deck_serial_numbers_with_set_default_page(self) -> list[str]:
        return self.v2.get_all_default_page_serial_numbers()
    
    def get_all_deck_serial_numbers_with_page_as_default(self, path: str) -> list[str]:
        return self.v2.get_serial_numbers_from_page(path)
    
    def move_page(self, old_path: str, new_path: str):
        self.v2.move_page(old_path, new_path)

    def remove_page(self, page_path: str):
        self.v2.remove_page(page_path)


    def add_page(self, name:str, page_dict: dict = None):
        self.v2.add_page(name, page_dict)

    def register_page(self, path: str):
        self.v2.register_page(path)

    def unregister_page(self, path: str):
        self.v2.unregister_page(path)

    def get_pages_with_path(self, page_path: str) -> list[Page]:
        self.v2.get_pages_with_path(page_path)
    
    def reload_pages_with_path(self, page_path: str) -> None:
        self.v2.reload_pages_with_path(page_path)

    def reload_all_pages(self) -> None:
        self.v2.reload_all_pages()

    def update_dict_of_pages_with_path(self, page_path: str) -> None:
        self.v2.update_dict_of_pages_with_path(page_path)

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
        return self.v2.get_page_data(page_path)
        
    def remove_asset_from_all_pages(self, path: str):
        self.v2.remove_asset_from_all_pages(path)

    def get_best_page_path_match_from_name(self, name: str) -> str:
        return self.v2.find_matching_page_path(name)
    
    def backup_pages(self) -> None:
        self.v2.backup_pages()


    def remove_old_backups(self) -> None:
        self.v2.remove_old_backups()
