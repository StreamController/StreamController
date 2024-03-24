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
import subprocess
import threading
import time

import globals as gl

class DesktopGrabber:
    def __init__(self):
        self.environment = self.get_active_environment()
        self.active_window_class: str = None

        if self.environment == "hyprland":
            self.grabber = HyprlandGrabber(self)

        self.classes = self.get_class_preferences()

    def get_active_environment(self) -> str:
        return os.getenv("XDG_CURRENT_DESKTOP").lower()
    
    def on_window_change(self, window_class: str) -> None:
        for controller in gl.deck_manager.deck_controller:
            if window_class in self.classes[controller.deck.get_serial_number()]:
                page_path = self.classes[controller.deck.get_serial_number()][window_class]
                page = gl.page_manager.get_page(page_path, controller)
                if not controller.page_auto_loaded:
                    controller.last_manual_loaded_page_path = controller.active_page.json_path
                controller.load_page(page, allow_reload=False)
                controller.page_auto_loaded = True

            elif controller.page_auto_loaded:
                last_manual_path = controller.last_manual_loaded_page_path
                if last_manual_path is None:
                    continue
                last_manual_page = gl.page_manager.get_page(last_manual_path, controller)
                controller.load_page(last_manual_page, allow_reload=False)
                controller.page_auto_loaded = False
                controller.last_manual_loaded_page_path = None


    def get_class_preferences(self) -> dict:
        classes = {}

        for deck_settings in os.listdir(os.path.join(gl.DATA_PATH, "settings", "decks")):
            splitext = os.path.splitext(deck_settings)
            
            classes[splitext[0]] = {}

            with open(os.path.join(gl.DATA_PATH, "settings", "decks", deck_settings), "r") as f:
                window_classes = json.load(f).get("window-classes", {})

                for class_name, page_path in window_classes.items():
                    classes[splitext[0]][class_name] = page_path



        return classes


class HyprlandGrabber:
    def __init__(self, desktop_grabber: DesktopGrabber):
        self.desktop_grabber = desktop_grabber

        self.active_window_class = self.get_active_window_class()

        grabber_thread = threading.Thread(target=self.fetch_active_window_class, daemon=True)
        grabber_thread.start()

    def get_active_window_class(self) -> str:
        result =  subprocess.check_output(["hyprctl", "activewindow", "-j"]).decode("utf-8")
        return json.loads(result).get("class").lower()


    def fetch_active_window_class(self) -> None:
        while True:
            new_window_class = self.get_active_window_class()
            if new_window_class != self.active_window_class:
                self.active_window_class = new_window_class
                self.desktop_grabber.on_window_change(self.active_window_class)

            time.sleep(0.5)