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

from datetime import datetime
import json
import os
import re
import shutil
import threading
from src.backend.DeckManagement.DeckController import DeckController
from src.backend.DeckManagement.InputIdentifier import Input, InputIdentifier
from src.backend.PageManagement.Page import Page
import globals as gl
from loguru import logger as log

class PredictionManager:
    def __init__(self):
        self.path = os.path.join(gl.DATA_PATH, "input-log", "input-log.json")
        os.makedirs(os.path.join(gl.DATA_PATH, "input-log"), exist_ok=True)

        self.write_lock = threading.Lock()

        self.dict: dict = {}
        self.history: dict = {}

        self.load()

    def save(self):
        with self.write_lock:
            with open(self.path, "w") as f:
                json.dump(self.dict, f, indent=4)

    def load(self):
        if not os.path.exists(self.path):
            return

        self.dict = {}        
        try:
            with open(self.path, "r") as f:
                self.dict = json.load(f)
        except Exception as e:
            backup_path = os.path.join(gl.DATA_PATH, "input-log", "backups", str(datetime.now().isoformat()))
            os.makedirs(os.path.dirname(backup_path), exist_ok=True)
            shutil.copy2(self.path, backup_path)
            log.error(f"Failed to load input-log.json. Backed up to {backup_path}: {e}")

    def add_entry(self, controller: DeckController, page: Page, identifier: InputIdentifier):
        deck_serial = controller.serial_number()
        page_hash = page.get_hash()

        self.dict.setdefault(deck_serial, {})
        self.dict[deck_serial].setdefault(page_hash, [])
        self.dict[deck_serial][page_hash].append({
            "history": list(self.history.get(deck_serial, {}).get(page_hash, [])),
            "next": f"{page_hash}::{str(identifier)}",
            "timestamp": datetime.now().isoformat()
        })

        self.save()

        # Update history
        self.history.setdefault(deck_serial, {})
        self.history[deck_serial].setdefault(page_hash, [])
        self.history[deck_serial][page_hash].append(f"{page_hash}::{str(identifier)}")
        self.history[deck_serial][page_hash] = self.history[deck_serial][page_hash][-10:]

    def find_matching_answers(self, controller: DeckController, page: Page) -> InputIdentifier:
        deck_serial = controller.serial_number()
        page_hash = page.get_hash()

        answers: list[str] = []
        for entry in self.dict.get(deck_serial, {}).get(page_hash, []):
            if entry["history"] == self.history.get(deck_serial, {}).get(page_hash, []):
                answers.append(entry["next"])

        return answers
    
    def most_frequent(self, List):
        if len(List) == 0:
            return
        return max(set(List), key = List.count)

    def get_prediction(self, controller: DeckController, page: Page) -> InputIdentifier:
        answers = self.find_matching_answers(controller, page)
        most_common = self.most_frequent(answers)
        if most_common is None:
            return

        pattern = r'::Input\((\w+),\s*([^)]+)\)'
        match = re.search(pattern, most_common)

        if match:
            input_type = match.group(1)
            json_identifier = match.group(2)
            return Input.FromTypeIdentifier(input_type, json_identifier)