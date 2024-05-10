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

class StreamDeckUIImporter:
    def __init__(self, json_export_path: str):
        self.json_export_path = json_export_path

    @lru_cache(maxsize=None)
    def index_to_page_coords(self, index: int, deck_serial: int) -> str:
        # Find deck
        rows, cols = 3, 5
        for deck_controller in gl.app.deck_manager.deck_controller:
            if deck_controller.serial_number() == deck_serial:
                rows, cols = deck_controller.deck.key_layout()
                break
        y = index // cols
        x = index % cols
        return f"{x}x{y}"
    
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
            
    def get_state_map(self, available_states: list[str]):
        available_states = [int(state) for state in available_states]
        available_states.sort()

        state_map = {}
        for i, original_number in enumerate(available_states):
            state_map[str(i)] = str(original_number)

        return state_map

    def perform_import(self):
        with open(self.json_export_path) as f:
            self.export = json.load(f)


        for deck in self.export.get("state", {}):
            ## Deck preferences
            preferences = {}
            preferences["brightness"] = {}
            preferences["screensaver"] = {}
            preferences["screensaver"]["enable"] = True
            preferences["brightness"]["value"] = self.export["state"][deck].get("brightness", 75)
            preferences["screensaver"]["time-delay"] = self.export["state"][deck].get("display_timeout", 5*60)//60
            preferences["screensaver"]["brightness"] = self.export["state"][deck].get("brightness_dimmed", 0)

            self.save_json(os.path.join(gl.DATA_PATH, "settings", "decks", f"{deck}.json"), preferences)

            for page_name in self.export["state"][deck].get("buttons", {}):
                ## Keys
                page = {}
                page["keys"] = {}

                for button in self.export["state"][deck]["buttons"][page_name]:
                    coords = self.index_to_page_coords(int(button), deck)
                    page["keys"][coords] = {}

                    # Choose first state
                    states = self.export["state"][deck]["buttons"][page_name][button]["states"]
                    state_map = self.get_state_map(available_states=list(states.keys()))
                    for page_state, export_state in state_map.items():
                        page["keys"][coords].setdefault("states", {})
                        page["keys"][coords]["states"].setdefault(page_state, {})

                        ## Text
                        font_color_hex = self.export["state"][deck]["buttons"][page_name][button]["states"][export_state].get("font_color")
                        if font_color_hex in [None, ""]:
                            font_color_hex = "#FFFFFFFF"
                        page["keys"][coords]["states"][page_state]["labels"] = {}
                        page["keys"][coords]["states"][page_state]["labels"]["bottom"] = {
                            "text": self.export["state"][deck]["buttons"][page_name][button]["states"][export_state].get("text", None),
                            "color": hex_to_rgba255(font_color_hex),
                            "font_size": None,
                            "font_family": font_family_from_path(self.export["state"][deck]["buttons"][page_name][button]["states"][export_state].get("font"))
                        }
                        
                        page["keys"][coords]["states"][page_state]["background"] = {}
                        color_hex = self.export["state"][deck]["buttons"][page_name][button]["states"][export_state].get("background_color")
                        if color_hex not in [None, ""]:
                            page["keys"][coords]["states"][page_state]["background"]["color"] = hex_to_rgba255(color_hex)

                        ## Icon
                        page["keys"][coords]["states"][page_state]["media"] = {}
                        export_icon = self.export["state"][deck]["buttons"][page_name][button]["states"][export_state].get("icon")
                        if export_icon not in [None, ""]:
                            if os.path.exists(export_icon):
                                asset_id = gl.asset_manager_backend.add(asset_path=export_icon)
                                asset = gl.asset_manager_backend.get_by_id(asset_id)
                                page["keys"][coords]["states"][page_state]["media"]["path"] = asset["internal-path"]
                            else:
                                log.warning(f"Icon {export_icon} not found, skipping")

                        ## Actions
                        page["keys"][coords]["states"][page_state]["actions"] = []

                        # Switch page
                        export_switch_page = self.export["state"][deck]["buttons"][page_name][button]["states"][export_state].get("switch_page")
                        if str(export_switch_page) != str(int(page_name)+1) and export_switch_page not in [0, "0", None, ""]:
                            if export_switch_page not in [None, ""]:
                                page_path = os.path.join(gl.DATA_PATH, "pages", f"ui_{deck}_{export_switch_page}.json")
                                action = {
                                    "id": "com_core447_DeckPlugin::ChangePage",
                                    "settings": {
                                        "selected_page": page_path,
                                        "deck_number": None
                                    }
                                }
                                page["keys"][coords]["states"][page_state]["actions"].append(action)

                        # Hotkey
                        if self.export["state"][deck]["buttons"][page_name][button]["states"][export_state].get("keys") not in [None, ""]:
                            parsed = ""
                            try:
                                parsed = parse_keys_as_keycodes(self.export["state"][deck]["buttons"][page_name][button]["states"][export_state]["keys"])[0]
                            except Exception as e:
                                log.error(f"Failed to parse keys: {self.export['state'][deck]['buttons'][page_name][button]['states'][export_state]['keys']}. Error: {e}")

                            if parsed not in [None, ""]:
                                action = {
                                    "id": "com_core447_OSPlugin::Hotkey",
                                    "settings": {
                                        "keys": []
                                    }
                                }
                                for key in parsed:
                                    action["settings"]["keys"].append([key, 1]) # Press

                                for key in parsed:
                                    action["settings"]["keys"].append([key, 0]) # Release

                                page["keys"][coords]["states"][page_state]["actions"].append(action)

                        # Write text
                        export_write = self.export["state"][deck]["buttons"][page_name][button]["states"][export_state].get("write")
                        if export_write not in [None, ""]:
                            action = {
                                "id": "com_core447_OSPlugin::WriteText",
                                "settings": {
                                    "text": export_write
                                }
                            }
                            page["keys"][coords]["states"][page_state]["actions"].append(action)

                        # Command
                        export_command = self.export["state"][deck]["buttons"][page_name][button]["states"][export_state].get("command")
                        if export_command not in [None, ""]:
                            action = {
                                "id": "com_core447_OSPlugin::RunCommand",
                                "settings": {
                                    "command": export_command
                                }
                            }
                            page["keys"][coords]["states"][page_state]["actions"].append(action)

                        # Brightness
                        export_brightness_change = self.export["state"][deck]["buttons"][page_name][button]["states"][export_state].get("brightness_change")
                        if export_brightness_change not in [None, "", 0]:
                            action = None
                            if export_brightness_change > 0:
                                action = {
                                    "id": "com_core447_DeckPlugin::IncreaseBrightness",
                                    "settings": {}
                                }
                            else:
                                action = {
                                    "id": "com_core447_DeckPlugin::DecreaseBrightness",
                                    "settings": {}
                                }
                            page["keys"][coords]["states"][page_state]["actions"].append(action)


                page_path = os.path.join(gl.DATA_PATH, "pages", f"ui_{deck}_{int(page_name) + 1}.json")
                self.save_json(page_path, page)
                # gl.signal_manager.trigger_signal(Signals.PageAdd, page_path) # We don't trigger the action to save ressources
                # time.sleep(0.005) # Otherwise the app can't hold up - The problem is the signal call, but is is necessary to 

                gl.page_manager.update_dict_of_pages_with_path(page_path)
                gl.page_manager.reload_pages_with_path(page_path)
                log.success(f"Imported page {page_name} as page ui_{int(page_name) + 1} on deck {deck}")

            log.success(f"Imported all pages of deck {deck}")

        log.success("Imported all pages from StreamDeck UI")

        if recursive_hasattr(gl, "app.main_win.sidebar.page_selector"):
            GLib.idle_add(gl.app.main_win.sidebar.page_selector.update)
        if recursive_hasattr(gl, "page_manager_window.page_selector"):
            GLib.idle_add(gl.page_manager_window.page_selector.load_pages)
        log.success("Updated ui")