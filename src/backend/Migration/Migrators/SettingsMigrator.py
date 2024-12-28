from src.backend.Migration.JsonMigrator.JsonMigrator import JsonMigrator, JsonMigrationRule
from typing import List, Callable
from packaging.version import Version
import json

class SettingsMigrator(JsonMigrator):
    def __init__(self, migration_file_path: str, from_version: str, to_version: str,
                 version_conditions: List[Callable[[Version, Version], bool]] = None, json_contains_version: bool = False) -> None:
        super().__init__(migration_file_path, from_version, to_version, version_conditions, json_contains_version)

    def migrate(self, migration_rules: list[JsonMigrationRule]):
        # Todo: Implement
        if not self.validate_version():
            return

        file = self.read_file()
        json_data = json.loads(file)

        if self.json_contains_version:
            self.migration_from = json_data.get("version")

        for rule in migration_rules:
            rule.apply(json_data)

        self.write_file(json.dumps(json_data))