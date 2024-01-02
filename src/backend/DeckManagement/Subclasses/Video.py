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
from loguru import logger as log
import os
import pickle
import gzip

class Video:
    def __init__(self):
        self.frames = []

    @log.catch
    def load_from_cache(self, file_name_without_extension):
        path = os.path.join("cache", file_name_without_extension)
        with gzip.open(path, "rb") as f:
            self.frames = pickle.load(f)

    @log.catch
    def save_to_cache(self, file_name_without_extension):
        path = os.path.join("cache", file_name_without_extension)
        with gzip.open(path, "wb") as f:
            pickle.dump(self.frames, f)