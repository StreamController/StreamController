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
# Import gtk modules
import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, Adw, GLib

# Import Python modules
import json
import os
import shutil
import uuid
from loguru import logger as log
from PIL import Image

# Import own modules
from src.backend.DeckManagement.HelperMethods import is_video, is_image, sha256, file_in_dir, create_empty_json, download_file, is_svg

# Import globals
import globals as gl


class AssetManagerBackend(list):
    JSON_PATH = os.path.join(gl.DATA_PATH, "Assets", "AssetManager", "Assets.json")
    def __init__(self):
        self.load_json()

        self.fill_missing_data()

        self.remove_invalid_data()

    def load_json(self):
        # Create file if it does not exist
        create_empty_json(self.JSON_PATH)
        # Load json file
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
            #TODO: It is possible that the some image has the same sha but not the name because it got renamed
            log.warning(f"Tried to add already existing asset. Ignoring. File: {asset_path}")
            id = self.get_by_sha256(hash)["id"]
            asset = self.get_by_id(id)
            return id
        
        # Copy asset to internal folder if it does not exist
        if not file_in_dir(os.path.basename(asset_path), os.path.join(gl.DATA_PATH, "cache")):
            internal_path = self.copy_asset(asset_path)
        
        thumbnail_path = internal_path
        
        if is_video(asset_path):
            thumbnail_path = self.save_thumbnail(asset_path, hash)

        if is_svg(asset_path):
            thumbnail_path = self.save_thumbnail(asset_path, hash)
            

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
            },
            "thumbnail": thumbnail_path
        }
        self.append(asset)

        # Save json
        self.save_json()

        # Return id of added asset
        return asset["id"]
    
    def save_thumbnail(self, asset_path, asset_hash):
        thumbnail_path = os.path.join(gl.DATA_PATH, "Assets", "AssetManager", "thumbnails", f"{asset_hash}.png")

        if os.path.exists(thumbnail_path):
            return thumbnail_path
        if not (is_video(asset_path) or is_svg(asset_path)):
            return asset_path
        
        # Create missing directories
        os.makedirs(os.path.join(gl.DATA_PATH, "Assets", "AssetManager", "thumbnails"), exist_ok=True)
        
        # Create thumbnail
        thumbnail = gl.media_manager.generate_thumbnail(asset_path)
        thumbnail.save(thumbnail_path)

        return thumbnail_path
    
    def remove_asset_by_id(self, id: str) -> None:
        asset = self.get_by_id(id)
        if asset is None:
            return
        
        internal_path = asset["internal-path"]

        gl.page_manager.remove_asset_from_all_pages(internal_path)

        os.remove(internal_path)

        self.remove(asset)
        self.save_json()
        
        
    def copy_asset(self, asset_path: str) -> str:
        file_name = os.path.basename(asset_path)
        dst_path = None
        if not file_in_dir(file_name, os.path.join(gl.DATA_PATH, "Assets", "AssetManager", "Assets")):
            dst_path = os.path.join(gl.DATA_PATH, "Assets", "AssetManager", "Assets", file_name)
        else:
            log.warning(f"File with same name already exists but sha256 does not match, renaming: {asset_path}")
            index = 2
            while file_in_dir(file_name, os.path.join(gl.DATA_PATH, "Assets", "AssetManager", "Assets")):
                base, ext = os.path.splitext(file_name)
                file_name = f"{base}-{str(index).zfill(2)}.{ext.replace('.', '')}"
            dst_path = os.path.join(gl.DATA_PATH, "Assets", "AssetManager", "Assets", file_name)

        if asset_path == dst_path:
            return asset_path

        try:
            # Ensure the dst dir is available
            os.makedirs(os.path.dirname(dst_path), exist_ok=True)
            # Copy file into internal asset dir
            shutil.copy(asset_path, dst_path)
        except shutil.SameFileError:
            log.warning(f"File already exists: {dst_path}")
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
    
    def has_by_internal_path(self, internal_path: str) -> bool:
        return self.get_by_internal_path(internal_path) is not None

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
            
    def get_by_internal_path(self, internal_path: str) -> dict:
        for asset in self:
            if asset["internal-path"] == internal_path:
                return asset
            
    def get_all(self) -> list:
        return self
    
    def fill_missing_data(self):
        def fill_missing_folders():
            os.makedirs(os.path.join(gl.DATA_PATH, "Assets", "thumbnails"), exist_ok=True)

        def fill_missing_thumbnails():
            for asset in self:
                if "thumbnail" in asset:
                    if os.path.exists(asset["thumbnail"]):
                        continue

                # Create thumbnail
                thumbnail_path = self.save_thumbnail(asset["internal-path"], asset["sha256"])

                asset["thumbnail"] = thumbnail_path

        
        fill_missing_folders()
        fill_missing_thumbnails()

        # Save
        self.save_json()

    def remove_invalid_data(self):
        ## Remove assets that have been delted internally
        for asset in self:
            if not os.path.exists(asset["internal-path"]):
                self.remove(asset)
        self.save_json()

    def add_custom_media_set_by_ui(self, url: str, path: str):
        window = gl.app.main_win
        if gl.store is not None:
            window = gl.store
            
        if path is None and url is not None:
            # Lower domain and remove point
            extension = os.path.splitext(url)[1].lower().replace(".", "")
            if extension not in (set(gl.VIDEO_EXTENSIONS) | set(gl.IMAGE_EXTENSIONS) | set(gl.SVG_EXTENSIONS)):

                # Not a valid url
                dial = Gtk.AlertDialog(
                    message="The image is invalid.",
                    detail="You can only use urls directly pointing to images (not directly from Google).",
                    modal=True
                )
                GLib.idle_add(dial.show)
                return -1

            os.makedirs(os.path.join(gl.DATA_PATH, "cache", "downloads"), exist_ok=True)
            # Download file from url
            path = download_file(url=url, path=os.path.join(gl.DATA_PATH, "cache", "downloads"))

        if path == None:
            return
        if not os.path.exists(path):
            return
        if not is_video(path) and not is_image(path) and not is_svg(path):
            dial = Gtk.AlertDialog(
                    message="No valid image or video.",
                    detail="Only images and videos are supported.",
                    modal=True
                )
            GLib.idle_add(dial.show)
            return
        asset_id = gl.asset_manager_backend.add(asset_path=path)
        if asset_id == None:
            return
        
        asset = self.get_by_id(asset_id)
        # Add to asset chooser ui if opened
        if gl.asset_manager is not None:
            gl.asset_manager.asset_chooser.custom_asset_chooser.add_asset(asset)

        return asset.get("internal-path")