from functools import lru_cache
import os
import json
import time

from src.backend.DeckManagement.HelperMethods import recursive_hasattr
from src.backend.DeckManagement.InputIdentifier import Input
from src.backend.PageManagement import PageBundle
from src.backend.Utils.AtomicSaveUtils import atomic_save_json
from src.windows.PageManager.Importer.StreamDeckUI.helper import font_family_from_path, hex_to_rgba255
from src.windows.PageManager.Importer.StreamDeckUI.code_conv import parse_keys_as_keycodes

from src.Signals import Signals
from loguru import logger as log

import globals as gl

import gi
from gi.repository import GLib

class StreamControllerImporter:
    def __init__(self, json_export_path: str, rename_to: str = None):
        self.json_export_path = json_export_path
        # Name to save a single imported page under, chosen by the user
        self.rename_to = rename_to


    def save_json(self, json_path: str, data: dict, _retries: int = 3):
        atomic_save_json(json_path, data, indent=4)

        loaded = None
        try:
            with open(json_path) as f:
                loaded = json.load(f)
        except Exception as e:
            pass

        if loaded != data:
            if _retries > 0:
                log.error(f"Failed to save {json_path}, trying again ({_retries} retries left)")
                self.save_json(json_path, data, _retries=_retries - 1)
            else:
                log.error(f"Failed to save {json_path} after all retries, giving up")
            
    def load_export(self) -> dict:
        """Returns {page name: page dict}, importing the assets of a bundle if there are any."""
        if PageBundle.is_bundle(self.json_export_path):
            return PageBundle.load_bundle(self.json_export_path)

        with open(self.json_export_path) as f:
            export = json.load(f)

        # A single exported page holds its config at the top level instead of a list of pages
        if any(key in export for key in ("settings", *Input.KeyTypes)):
            return {os.path.splitext(os.path.basename(self.json_export_path))[0]: export}

        return export

    def perform_import(self):
        self.export = self.load_export()

        for page_name in self.export:
            page = self.export[page_name]
            if self.rename_to is not None and len(self.export) == 1:
                page_name = self.rename_to
            page_path = os.path.join(gl.DATA_PATH, "pages", f"{page_name}.json")
            if ".json.json" in page_path:
                page_path = page_path.replace(".json.json", ".json")

            is_new_page = not os.path.exists(page_path)

            self.save_json(page_path, page)

            gl.page_manager.update_dict_of_pages_with_path(page_path)
            gl.page_manager.reload_pages_with_path(page_path)

            if is_new_page:
                gl.signal_manager.trigger_signal(Signals.PageAdd, page_path)

            log.success(f"Imported page {page_name}")

        log.success("Imported all pages from StreamController")

        if recursive_hasattr(gl, "app.main_win.sidebar.page_selector"):
            GLib.idle_add(gl.app.main_win.sidebar.page_selector.update)
        if recursive_hasattr(gl, "page_manager_window.page_selector"):
            GLib.idle_add(gl.page_manager_window.page_selector.load_pages)
        log.success("Updated ui")