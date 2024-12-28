from abc import abstractmethod

from src.backend.Migration.MigrationBase import MigrationBase
from .JsonMigrationRule import JsonMigrationRule
from typing import List, Callable
from packaging.version import Version

class JsonMigrator(MigrationBase):
    def __init__(self, migration_file_path: str, from_version: str, to_version: str,
                 version_conditions: List[Callable[[Version, Version], bool]] = None, json_contains_version: bool = False) -> None:
        super().__init__(migration_file_path, from_version, to_version, version_conditions)

        self.json_contains_version = json_contains_version

    @abstractmethod
    def migrate(self, migration_rules: list[JsonMigrationRule]):
        pass