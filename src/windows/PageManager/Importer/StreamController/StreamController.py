from functools import lru_cache
import os
import json
import time

from src.backend.DeckManagement.HelperMethods import recursive_hasattr
from src.windows.PageManager.Importer.StreamDeckUI.helper import font_family_from_path, hex_to_rgba255
from src.windows.PageManager.Importer.StreamDeckUI.code_conv import parse_keys_as_keycodes

from src.Signals import Signals
from loguru import logger as log

import globals as gl

import gi
from gi.repository import GLib

class StreamControllerImporter:
    def __init__(self, json_export_path: str):
        self.json_export_path = json_export_path

    
    def save_json(self, json_path: str, data: dict):
        with open(json_path, "w") as f:
            json.dump(data, f, indent=4)

        loaded = None
        try:
            # Verify data
            with open(json_path) as f:
                loaded = json.load(f)
        except Exception as e:
            pass

        if loaded != data:
            log.error(f"Failed to save {json_path}, trying again")
            self.save_json(json_path, data)
            
    def perform_import(self):
        with open(self.json_export_path) as f:
            self.export = json.load(f)

        for page_name in self.export:
            page = self.export[page_name]
            page_path = os.path.join(gl.CONFIG_PATH, "pages", f"{page_name}.json")
            if ".json.json" in page_path:
                page_path = page_path.replace(".json.json", ".json")
            
            self.save_json(page_path, page)

            gl.page_manager.update_dict_of_pages_with_path(page_path)
            gl.page_manager.reload_pages_with_path(page_path)

            log.success(f"Imported page {page_name}")

        log.success("Imported all pages from StreamController")

        if recursive_hasattr(gl, "app.main_win.sidebar.page_selector"):
            GLib.idle_add(gl.app.main_win.sidebar.page_selector.update)
        if recursive_hasattr(gl, "page_manager_window.page_selector"):
            GLib.idle_add(gl.page_manager_window.page_selector.load_pages)
        log.success("Updated ui")
