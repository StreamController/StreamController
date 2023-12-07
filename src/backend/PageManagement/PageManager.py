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
# Import Python modules
import os
import shutil
import json
from copy import copy

# Import own modules
from src.backend.PageManagement.Page import Page

# Import globals
import globals as gl

class PageManager:
    def __init__(self, settings_manager):
        self.settings_manager = settings_manager

        self.created_pages = {}
    
    def save_pages(self) -> None:
        for page in self.pages.values():
            page.save()

    def get_pages(self, remove_extension: bool = False) -> list:
        pages = []
        # Create pages dir if it doesn't exist
        os.makedirs("pages", exist_ok=True)
        # Get all pages
        for page in os.listdir("pages"):
            if os.path.splitext(page)[1] == ".json":
                if remove_extension:
                    page = os.path.splitext(page)[0]
                pages.append(page)
        return pages
    
    def create_page_for_name(self, name: str, deck_controller: "DeckController") -> Page:
        if os.path.splitext(name)[1] != ".json":
            name += ".json"
        page = Page(json_path=os.path.join("pages", name), deck_controller=deck_controller)
        self.created_pages.setdefault(deck_controller, {})
        self.created_pages[deck_controller][name] = page
        return page
    
    def get_page(self, name: str, deck_controller: "DeckController") -> Page:
        if os.path.splitext(name)[1] != ".json":
            name += ".json"
        
        if deck_controller in self.created_pages:
            if name in self.created_pages[deck_controller]:
                return self.created_pages[deck_controller][name]
            
        return self.create_page_for_name(name, deck_controller)

    def get_default_page_for_deck(self, serial_number: str, remove_extension: bool = False) -> Page:
        page_settings = self.settings_manager.load_settings_from_file("settings/pages.json")
        for page in page_settings.get("default-pages", []):
            if page["deck"] == serial_number:
                name = page["name"]
                if not remove_extension:
                    name += ".json"
                return name
        return None
    
    def rename_page(self, old_name: str, new_name: str):
        old_path = os.path.join("pages", f"{old_name}.json")
        new_path = os.path.join("pages", f"{new_name}.json")

        # Copy page json file
        shutil.copy2(old_path, new_path)

        # Change name in page objects
        for controller in gl.deck_manager.deck_controller:
            if controller.active_page is None:
                continue
            page = self.get_page(old_name, controller)
            if page is None:
                continue
            page.json_path = new_path
            
            # Update default page settings
            settings = gl.settings_manager.load_settings_from_file("settings/pages.json")
            if settings.get("default-pages") is None:
                continue
            for entry in settings["default-pages"]:
                if entry["name"] == old_name:
                    entry["name"] = new_name
                    gl.settings_manager.save_settings_to_file("settings/pages.json", settings)

        # Remove old page
        os.remove(old_path)

        # Update ui
        gl.app.main_win.header_bar.page_selector.update()


    def remove_page(self, name: str):
        # Clear page objects
        for controller in gl.deck_manager.deck_controller:
            if controller.active_page is None:
                continue
            page = self.get_page(name, controller)
            if page is None:
                continue

            if controller.active_page.get_name() != name:
                continue


            deck_default_page = self.get_default_page_for_deck(controller.deck.get_serial_number(), remove_extension=True)
            if name != deck_default_page:
                new_page = self.get_page(deck_default_page, controller)
                controller.load_page(new_page)
                continue

            if name == deck_default_page:
                page_list = self.get_pages(remove_extension=True)
                page_list.remove(name)
                controller.load_page(self.get_page(page_list[0], controller))


        # Remove page json file
        os.remove(os.path.join("pages", f"{name}.json"))

        # Remove default page entries
        settings = gl.settings_manager.load_settings_from_file("settings/pages.json")
        for entry in copy(settings.get("default-pages",[])):
            if entry["name"] == name:
                settings["default-pages"].remove(entry)
        gl.settings_manager.save_settings_to_file("settings/pages.json", settings)

        # Update ui
        gl.app.main_win.header_bar.page_selector.update()

    def add_page(self, name:str):
        page = {
            "keys": {}
        }

        with open(os.path.join("pages", f"{name}.json"), "w") as f:
            json.dump(page, f)

        # Update ui
        gl.app.main_win.header_bar.page_selector.update()