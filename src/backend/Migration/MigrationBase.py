from abc import abstractmethod, ABC

from src.backend.Migration.MigrationCondition import MigrationCondition
from src.backend.Migration.MigrationAction import MigrationAction
from loguru import logger as log

class MigrationBase(ABC):
    def __init__(self,
                 migration_actions: list[MigrationAction],
                 migration_conditions: list[MigrationCondition],
                 dependant_migrator: "MigrationBase" = None,
                 ignore_backup_success: bool = False):
        self.migration_actions: list[MigrationAction] = migration_actions # Actions for the migration
        self.migration_conditions: list[MigrationCondition] = migration_conditions # Conditions when to apply migration
        self.dependant_migrator: "MigrationBase" = dependant_migrator # Migrator that should run before this one
        self.ignore_backup_success: bool = ignore_backup_success

        self.migration_ran: bool = False # If the migration already ran or not
        self.migration_success: bool = False # If the migration was successful

    def migrate(self) -> bool:
        """Public function that gets called for migration"""

        log.info(f"{self.__class__.__name__}: START RUNNING MIGRATION ROUTINE")

        # Run dependant migrator if it exists
        if self.dependant_migrator:
            log.info(f"{self.__class__.__name__}: DEPENDANT MIGRATOR FOUND. MIGRATOR={self.dependant_migrator.__class__.__name__}")
            self._run_dependant_migrator()

            # Todo: Implement better way to check if next migrator should run
            log.info(f"{self.__class__.__name__}: DEPENDANT MIGRATOR ({self.dependant_migrator.__class__.__name__}) SUCCESS=({self.dependant_migrator.migration_success})")
            if not self.dependant_migrator.migration_success:
                return False

        # Check if backup is successful or if it can be ignored
        log.info(f"{self.__class__.__name__}: STARTING BACKUP FOR MIGRATOR")
        log.info(f"{self.__class__.__name__}: IGNORING BACKUP FAILURE ({self.ignore_backup_success})")
        if not self._backup() or self.ignore_backup_success:
            return False

        log.info(f"{self.__class__.__name__}: CHECKING MIGRATION CONDITIONS")
        # Only start migrating if conditions are met
        if not self._check_conditions():
            return False

        # Try migration
        log.info(f"{self.__class__.__name__}: TRYING TO MIGRATE")
        if self._migrate():
            self.migration_success = True


        log.info(f"{self.__class__.__name__}: MIGRATION SUCCESS={self.migration_success}")

        self.migration_ran = True

    def _run_dependant_migrator(self):
        if not self.dependant_migrator.migration_ran:
            log.info(f"RUNNING DEPENDANT MIGRATOR: {self.__class__.__name__}")
            self.dependant_migrator.migrate()

    @abstractmethod
    def _migrate(self) -> bool:
        """Function that should be overridden for migration"""
        pass

    def _check_conditions(self) -> bool:
        return all(condition.check() for condition in self.migration_conditions)

    def _write_file(self):
        pass

    def _read_file(self):
        pass

    def _backup(self) -> bool:
        return True