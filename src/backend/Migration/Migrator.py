import json
import globals as gl
import os
from packaging import version

class Migrator:
    SETTINGS_DIR = os.path.join(gl.DATA_PATH, "settings", "migrations.json")
    def __init__(self, app_version: str):
        self.app_version = app_version
        self.parsed_app_version = version.parse(app_version)

    def get_need_migration(self) -> bool:
        if version.parse(gl.app_version) < version.parse(self.app_version) and False:
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