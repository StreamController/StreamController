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
import json
import shutil
import globals as gl
import os
from packaging import version
from loguru import logger as log

class Migrator:
    SETTINGS_DIR = os.path.join(gl.DATA_PATH, "settings", "migrations.json")
    def __init__(self, app_version: str):
        self.app_version = app_version
        self.parsed_app_version = version.parse(app_version)

    def get_need_migration(self) -> bool:
        app_version = version.parse(gl.app_version)
        migrator_version = self.parsed_app_version
        if app_version < migrator_version:
            return False

        settings = self.get_settings()
        return not settings.get(self.app_version, False)
    
    def set_migrated(self, migrated: bool) -> None:
        settings = self.get_settings()
        settings[self.app_version] = migrated
        self.set_settings(settings)

    def get_settings(self) -> dict:
        """
        SettingsManager is not yet loaded when this is called
        """
        if not os.path.exists(self.SETTINGS_DIR):
            return {}
        with open(self.SETTINGS_DIR, "r") as f:
            return json.load(f)
        
    def set_settings(self, settings: dict) -> None:
        """
        SettingsManager is not yet loaded when this is called
        """
        os.makedirs(os.path.dirname(self.SETTINGS_DIR), exist_ok=True)
        with open(self.SETTINGS_DIR, "w") as f:
            json.dump(settings, f, indent=4)

    def create_backup(self) -> None:
        pages_path = os.path.join(gl.DATA_PATH, "pages")
        if not os.path.exists(pages_path):
            return
        backup_path = os.path.join(gl.DATA_PATH, "backups")
        os.makedirs(backup_path, exist_ok=True)

        # Create zip
        log.info(f"Creating backup to {backup_path}")
        path = shutil.make_archive(
            base_name=os.path.join(backup_path, f"before_{gl.app_version}_migration"),
            format="zip",
            root_dir=pages_path,
        )
        log.success(f"Saved backup to {path}")