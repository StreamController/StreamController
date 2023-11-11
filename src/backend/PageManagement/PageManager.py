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

# Import own modules
from src.backend.PageManagement.Page import Page

class PageManager:
    def __init__(self, settings_manager):
        self.settings_manager = settings_manager
    
    def save_pages(self) -> None:
        for page in self.pages.values():
            page.save()

    def get_pages(self, remove_extension: bool = False) -> list:
        pages = []
        for page in os.listdir("pages"):
            if os.path.splitext(page)[1] == ".json":
                if remove_extension:
                    page = os.path.splitext(page)[0]
                pages.append(page)
        return pages
    
    def create_page_for_name(self, name: str, deck_controller: "DeckController") -> Page:
        if os.path.splitext(name)[1] != ".json":
            name += ".json"
        return Page(json_path=os.path.join("pages", name), deck_controller=deck_controller)

    def get_default_page_for_deck(self, serial_number: str, remove_extension: bool = False) -> Page:
        page_settings = self.settings_manager.load_settings_from_file("settings/pages.json")
        for page in page_settings["default-pages"]:
            if page["deck"] == serial_number:
                name = page["name"]
                if not remove_extension:
                    name += ".json"
                return name
        return None