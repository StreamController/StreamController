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
import json
import os
import shutil
import uuid
from loguru import logger as log

# Import own modules
from src.backend.DeckManagement.HelperMethods import sha256, file_in_dir


class AssetManager(list):
    JSON_PATH = os.path.join("Assets", "AssetManager", "Assets.json")
    def __init__(self):
        self.load_json()

    def load_json(self):
        if not os.path.exists(self.JSON_PATH):
            log.warning("No JSON file found! Createing a new one.")
            self = []
            self.save()
            return
        with open(self.JSON_PATH, "r") as f:
            self.clear()
            content = json.load(f)
            self.extend(content)

    def save_json(self):
        with open(self.JSON_PATH, "w") as f:
            json.dump(self, f, indent=4)

    def add(self, asset_path: str, licence_name: str = None, licence_url: str = None, author: str = None) -> str:
        if not os.path.exists(asset_path):
            log.warning(f"File {asset_path} not found.")
            return
        
        hash = sha256(asset_path)
        if self.has_by_sha256(hash):
            log.warning(f"Tried to add already existing asset. Ignoring. File: {asset_path}")
            return
        
        # Copy asset to internal folder
        internal_path = self.copy_asset(asset_path)

        asset = {
            "name": os.path.splitext(os.path.basename(asset_path))[0],
            "original-path": asset_path,
            "internal-path": internal_path,
            "sha256": hash,
            "id": self.create_unique_uuid(),
            "license": {
                "name": licence_name,
                "url": licence_url,
                "author": author
            }
        }
        self.append(asset)

        # Save json
        self.save_json()

        # Return id of added asset
        return asset["id"]
        
    def copy_asset(self, asset_path: str) -> str:
        file_name = os.path.basename(asset_path)
        dst_path = None
        if not file_in_dir(file_name, "cache"):
            dst_path = os.path.join("Assets", "AssetManager", "Assets", file_name)
        else:
            log.warning(f"File with same name already exists but sha256 does not match, renaming: {asset_path}")
            index = 2
            while file_in_dir(file_name, "cache"):
                file_name = f"{file_name}-{str(index).zfill(2)}"
            dst_path = os.path.join("Assets", "AssetManager", "Assets", file_name)

        shutil.copy(asset_path, dst_path)
        return dst_path
    
    def create_unique_uuid(self) -> str:
        id = str(uuid.uuid4())
        if self.has_by_id(id):
            # For the unlike case that the id is already used
            log.warning("Congratulations, you already have an asset with this id. This is very rare.")
            return self.create_unique_uuid()
        return id

    def has_by_name(self, name: str) -> bool:
        return self.get_by_name(name) is not None
            
    def has_by_sha256(self, sha256: str) -> bool:
        return self.get_by_sha256(sha256) is not None

    def has_by_id(self, id: str) -> bool:
        return self.get_by_id(id) is not None

    def get_by_name(self, name: str) -> dict:
        for asset in self:
            if asset["name"] == name:
                return asset
            
    def get_by_sha256(self, sha256: str) -> dict:
        for asset in self:
            if asset["sha256"] == sha256:
                return asset
            
    def get_by_id(self, id: str) -> dict:
        for asset in self:
            if asset["id"] == id:
                return asset