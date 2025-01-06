import operator
import os
from concurrent.futures import ThreadPoolExecutor
from unittest import result

from src.backend.Migration.JsonMigrator.JsonAction import JsonAction
from src.backend.Migration.JsonMigrator.JsonMigrator import JsonMigrator
from src.backend.Migration.MigrationActions.JsonActions import MoveAction, AddAction, CompareAction
from src.backend.Migration.MigrationConditions.VersionCondition import VersionCondition
import json
import globals as gl
from loguru import logger as log

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from src.backend.Migration.MigrationBase import MigrationBase

class Settings_1_5_0_b8(JsonMigrator):
    def __init__(self,
                 dependant_migrator: "MigrationBase" = None,
                 ignore_backup_success: bool = False):
        migration_actions: list[JsonAction] = [CompareAction(["version"], None), MoveAction(["*"], ["settings"]), AddAction(["version"], "1.0")]
        migration_conditions = [VersionCondition(gl.app_version, "1.5.0.beta.8", operator.lt)]

        super().__init__(migration_actions, migration_conditions, dependant_migrator, ignore_backup_success)

    def _migrate(self) -> bool:
        log.log("MIGRATION_INFO", f"{self.__class__.__name__}: STARTED MIGRATING PLUGIN SETTINGS")

        settings_path = os.path.join(gl.DATA_PATH, "settings", "plugins")
        setting_files: dict[str, dict] = {}

        log.log("MIGRATION_INFO", f"{self.__class__.__name__}: RETRIEVING SETTING FILES")
        for root, dirs, files in os.walk(settings_path):
            if root == settings_path:
                continue

            if "settings.json" in files:
                path = os.path.join(root, "settings.json")
                with open(path, "r") as file:
                    setting_files[path] = json.load(file)

        log.log("MIGRATION_INFO", f"{self.__class__.__name__}: EXECUTING THREAD POOL TO MIGRATE SETTING FILES")
        with ThreadPoolExecutor() as executor:
            results = executor.map(self._migrate_settings_file, setting_files.items())

        success = all(results)

        if success:
            log.log("MIGRATION_SUCCESS", f"{self.__class__.__name__}: FINISHED MIGRATING PLUGIN SETTINGS. SUCCESS: {success}")
        else:
            log.log("MIGRATION_ERROR", f"{self.__class__.__name__}: FINISHED MIGRATING PLUGIN SETTINGS. SUCCESS: {success}")

        return success

    def _migrate_settings_file(self, item: tuple[str, dict]):
        path = item[0]
        json_data = item[1]

        log.log("MIGRATION_INFO", f"{self.__class__.__name__}: TRYING TO EXECUTE MIGRATION ACTIONS FOR {path}")
        try:
            for action in self.migration_actions:
                log.log("MIGRATION_INFO", f"{self.__class__.__name__}: EXECUTING ACTION {action.__class__.__name__} FOR {path}")
                if not action.apply(json_data):
                    log.log("MIGRATION_ERROR", f"{self.__class__.__name__}: FAILED EXECUTING ACTION {action.__class__.__name__} FOR {path}. ABORTING MIGRATION")
                    raise Exception()
            with open(path, "w") as file:
                file.write(json.dumps(json_data, indent=4))
            log.log("MIGRATION_INFO", f"{self.__class__.__name__}: MIGRATED SETTINGS FILE {path}")
            return True
        except Exception as e:
            log.log("MIGRATION_ERROR", f"ERROR WHILE MIGRATING SETTINGS FILE {path}: {e}")