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

import os
import csv
import locale

class LocaleManager:
    def __init__(self, csv_path: str) -> None:
        self.csv_path = csv_path
        self.language = "en_US"
        self.FALLBACK_LOCALE = "en_US"

        self.available_locales = []
        self.locale_data = {}

        self.load_csv()

    def load_csv(self) -> None:
        with open(self.csv_path, newline='') as csvfile:
            reader = csv.reader(csvfile, delimiter=';', quotechar='"', skipinitialspace=True)
            self.available_locales = next(reader)[1:]

            for row in reader:
                if row == []: continue
                self.locale_data[row[0]] = dict(zip(self.available_locales, row[1:]))

    def set_language(self, language: str) -> str:
        self.language = language

    def set_fallback_language(self, language: str) -> None:
        self.FALLBACK_LOCALE = language

    def set_to_os_default(self):
        os_locale = locale.getlocale()[0]
        self.set_language(os_locale)

    def get_best_match(self, preferred_language: str) -> str:
        # Get all available locales
        # Return preferred language if it exists
        if preferred_language in self.available_locales:
            return preferred_language

        # Get primary language code (eg. en for en_US)
        primary_language_code = preferred_language.split("_")[0]
        for language in self.available_locales:
            if language.startswith(primary_language_code):
                return language
        return self.FALLBACK_LOCALE

    def get_custom_translation(self, locale_json:dict[str, str]):
        if locale_json is None:
            return ""
        result = locale_json.get(self.language)
        if result in [None, ""]:
            return locale_json.get(self.FALLBACK_LOCALE)
        return result

    def get(self, key: str, fallback: str = None) -> str:
        key_dict = self.locale_data.get(key, {})

        result = key_dict.get(self.language)
        if result in [None, ""]:
            return key_dict.get(self.FALLBACK_LOCALE, key)
        if result is None:
            return key if fallback is None else fallback

        return result