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
    locales = None
    locales_json = None
    def __init__(self):
        pass

    def set_to_os_default(self):
        os_locale = locale.getlocale()[0]
        self.set_language(os_locale)

    def set_language(self, language):
        self.locales = language
        if os.path.isfile(os.path.join("locales", f"{self.locales}.json")) == False:
            #Default to en_US if language file does not exist
            self.locales = "en_US"
        with open(os.path.join("locales", f"{self.locales}.json")) as f:
            self.locales_json = json.load(f)
    
    def get(self, key):
        if self.locales_json is None:
            log.warning("No language set.")
            return key
        #TODO: If language does not have key, return automatic translation
        if key not in self.locales_json:
            print(key)
            # exit()
            return "Not found"
        return self.locales_json[key]