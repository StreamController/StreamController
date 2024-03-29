"""
Author: Core447
Year: 2024

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
any later version.

This programm comes with ABSOLUTELY NO WARRANTY!

You should have received a copy of the GNU General Public License
along with this program. If not, see <https://www.gnu.org/licenses/>.
"""

import json
import os
import re
import subprocess
import threading
import time
from loguru import logger as log

import globals as gl

from src.backend.WindowGrabber.Window import Window
from src.backend.WindowGrabber.Integration import Integration
from src.backend.WindowGrabber.Integrations.Hyprland import Hyprland
from src.backend.WindowGrabber.Integrations.Gnome import Gnome

class WindowGrabber:
    def __init__(self):
        self.SUPPORTED_ENVS = ["hyprland", "gnome"]

        self.integration: Integration = None
        self.init_integration()

    def get_active_environment(self) -> str:
        return os.getenv("XDG_CURRENT_DESKTOP").lower()
    
    def init_integration(self) -> None:
        self.environment = self.get_active_environment()
        if self.environment not in self.SUPPORTED_ENVS:
            log.error(f"Unsupported environment: {self.environment} for window grabber.")
            return
        
        log.info(f"Initializing window grabber for environment: {self.environment}")
        if self.environment == "hyprland":
            self.integration = Hyprland(self)
        elif self.environment == "gnome":
            self.integration = Gnome(self)

    def get_all_windows(self) -> list[Window]:
        """
        returns a list of [wm_class, title] lists
        """
        if self.integration is None:
            return []

        return self.integration.get_all_windows()
    
    def get_all_matching_windows(self, class_regex: str, title_regex: str) -> list[Window]:
        all_windows = self.get_all_windows()

        matching_windows: list[Window] = []
        for window in all_windows:
            if self.get_is_window_matching(window, class_regex, title_regex):
                matching_windows.append(window)

        return matching_windows
    
    def get_is_window_matching(self, window: Window, class_regex: str, title_regex: str) -> bool:
        if None in (window.wm_class, window.title, class_regex, title_regex):
            return False
        try:
            class_match = re.search(class_regex, window.wm_class, re.IGNORECASE)
            title_match = re.search(title_regex, window.title, re.IGNORECASE)
        except re.error:
            return False
        return class_match and title_match
    
    def on_active_window_changed(self, window: Window) -> None:
        log.info(f"Active window changed to: {window}")
        for deck_controller in gl.deck_manager.deck_controller:
            found_page = False
            for page_path in gl.page_manager.get_pages():
                abs_path = os.path.abspath(page_path)
                info = gl.page_manager.auto_change_info[abs_path]
                wm_regex = info.get("wm_class")
                title_regex = info.get("title")
                enabled = info.get("enable", False)
                if not enabled:
                    continue

                if self.get_is_window_matching(window, wm_regex, title_regex):
                    if not deck_controller.deck.is_open():
                        return
                    log.debug(f"Auto changing page: {page_path} on deck {deck_controller.deck.get_serial_number()}")
                    page = gl.page_manager.get_page(page_path, deck_controller)
                    if not deck_controller.page_auto_loaded:
                        deck_controller.last_manual_loaded_page_path = deck_controller.active_page.json_path
                    deck_controller.load_page(page)
                    deck_controller.page_auto_loaded = True
                    found_page = True
                    break

            if not found_page:
                if deck_controller.page_auto_loaded:
                    deck_controller.page_auto_loaded = False
                    if deck_controller.last_manual_loaded_page_path is None:
                        continue
                    page = gl.page_manager.get_page(deck_controller.last_manual_loaded_page_path, deck_controller)
                    deck_controller.load_page(page, allow_reload=False)