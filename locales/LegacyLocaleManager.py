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
import os
import json
import locale
from loguru import logger as log

class LegacyLocaleManager:
    def __init__(self, locales_path: str):
        self.locales_path: str = locales_path
        self.locales_json: dict = {}
        self.fallback_json: dict = {}
        self.locales: str = None
        self.FALLBACK_LOCALE: str = "en_US"

    def load_fallback_language(self):
        path = os.path.join(self.locales_path, f"{self.FALLBACK_LOCALE}.json")
        if not os.path.exists(path):
            log.warning(f"Fallback language file not found under: {path}")
            return
        with open(os.path.join(self.locales_path, f"{self.FALLBACK_LOCALE}.json")) as f:
            self.fallback_json = json.load(f)

    def set_to_os_default(self):
        os_locale = locale.getlocale()[0]
        self.set_language(os_locale)

    def set_language(self, language: str) -> str:
        language = self.get_best_match(language)
        self.locales = language
        
        if not os.path.isfile(os.path.join(self.locales_path, f"{self.locales}.json")):
            # We're gonna use the fallback language
            return

        with open(os.path.join(self.locales_path, f"{self.locales}.json")) as f:
            self.locales_json = json.load(f)

    def set_fallback_language(self, language: str) -> None:
        self.FALLBACK_LOCALE = language
        self.load_fallback_language()

    def get(self, key: str, fallback: str = None) -> str:
        return self.locales_json.get(key, self.fallback_json.get(key, fallback or key))
    
    def get_availbale_locales(self) -> list:
        locales: list[str] = []
        if not os.path.exists(self.locales_path):
            return locales
        for file in os.listdir(self.locales_path):
            if file.endswith(".json"):
                locales.append(os.path.splitext(file)[0])

        return locales
    
    def get_best_match(self, preferred_language: str) -> str:
        # Get all available locales
        available_locales = self.get_availbale_locales()
        # Return preferred language if it exists
        if preferred_language in available_locales:
            return preferred_language

        # Get primary language code (eg. en for en_US)
        primary_language_code = preferred_language.split("_")[0]
        for language in available_locales:
            if language.startswith(primary_language_code):
                return language
        return self.FALLBACK_LOCALE