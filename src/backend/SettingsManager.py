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
import os, json
from loguru import logger as log

# Import own modules
import globals as gl

class SettingsManager:
    def __init__(self):
        self.font_defaults: dict = {} # Used by the LabelManager to get the default font settings
        self.load_font_defaults()

    def load_settings_from_file(self, file_path: str) -> dict:
        if not os.path.exists(file_path):
            return {}
        try:
            with open(file_path) as f:
                return json.load(f)
        except json.decoder.JSONDecodeError as e:
            log.error(f"Invalid json in {file_path}: {e}")
            return {}
        
        
    def save_settings_to_file(self, file_path: str, settings: dict) -> None:
        # Create directories if they don't exist
        if not os.path.exists(os.path.dirname(file_path)) and os.path.dirname(file_path) != "":
            os.makedirs(os.path.dirname(file_path))

        with open(file_path, "w") as f:
            json.dump(settings, f, indent=4)

    def get_deck_settings(self, deck_serial_number: str) -> dict:
        """
        Retrieves the deck settings for a given deck serial number.
        This is just a wrapper around load_settings_from_file()

        Args:
            deck_serial_number (str): The serial number of the deck.

        Returns:
            dict: The deck settings loaded from the file.
        """
        path = os.path.join(gl.DATA_PATH, "settings", "decks", f"{deck_serial_number}.json")
        settings =  self.load_settings_from_file(path)
        if settings == None:
            settings = {}
            self.save_settings_to_file(path, settings)
        return settings
    
    def save_deck_settings(self, deck_serial_number: str, settings: dict) -> None:
        """
        Saves the settings for a deck.
        This is just a wrapper around save_settings_to_file()

        Args:
            deck_serial_number (str): The serial number of the deck.
            settings (dict): The settings to save.

        Returns:
            None
        """
        path = os.path.join(gl.DATA_PATH, "settings", "decks", f"{deck_serial_number}.json")
        self.save_settings_to_file(path, settings)

    def get_app_settings(self) -> dict:
        path = os.path.join(gl.DATA_PATH, "settings", "settings.json")
        settings =  self.load_settings_from_file(path)
        if settings == None:
            settings = {}
            self.save_settings_to_file(path, settings)
        return settings
    
    def save_app_settings(self, settings: dict) -> None:
        path = os.path.join(gl.DATA_PATH, "settings", "settings.json")
        self.save_settings_to_file(path, settings)

    def get_static_settings(self) -> dict:
        """
        Returns always the same settings, no matter what the data path is set to
        """
        return self.load_settings_from_file(gl.STATIC_SETTINGS_FILE_PATH)
    
    def save_static_settings(self, settings: dict) -> None:
        self.save_settings_to_file(gl.STATIC_SETTINGS_FILE_PATH, settings)

    def load_font_defaults(self) -> None:
        app_settings = self.get_app_settings()

        self.font_defaults = app_settings.get("general", {}).get("default-font", {})

    def save_font_defaults(self) -> None:
        app_settings = self.get_app_settings()
        app_settings["general"] = {}
        app_settings["general"]["default-font"] = self.font_defaults
        self.save_app_settings(app_settings)