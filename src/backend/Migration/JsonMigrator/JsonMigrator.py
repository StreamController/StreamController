from abc import abstractmethod

from src.backend.Migration.JsonMigrator.JsonAction import JsonAction
from src.backend.Migration.MigrationBase import MigrationBase
from src.backend.Migration.MigrationCondition import MigrationCondition

class JsonMigrator(MigrationBase):
    def __init__(self,
                 migration_actions: list[JsonAction],
                 migration_conditions: list[MigrationCondition],
                 dependant_migrator: "MigrationBase" = None,
                 ignore_backup_success: bool = False):
        super().__init__(migration_actions, migration_conditions, dependant_migrator, ignore_backup_success)

    @abstractmethod
    def _migrate(self) -> bool:
        pass