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

class LocaleManager:
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
        self.locales = language
        if not os.path.isfile(os.path.join(self.locales_path, f"{self.locales}.json")):
            # We're gonna use the fallback language
            return

        with open(os.path.join(self.locales_path, f"{self.locales}.json")) as f:
            self.locales_json = json.load(f)

    def set_fallback_language(self, language: str) -> None:
        self.FALLBACK_LOCALE = language
        self.load_fallback_language()

    def get(self, key: str) -> str:
        return self.locales_json.get(key, self.fallback_json.get(key, key))