from src.backend.Migration.Migrator import Migrator

from loguru import logger as log

class MigrationManager:
    def __init__(self):
        self.migrators: list[Migrator] = []
        pass

    def add_migrator(self, migrator: Migrator):
        self.migrators.append(migrator)

    def run_migrators(self):
        for migrator in self.get_ordered_migrators():
            if migrator.get_need_migration():
                log.info(f"Running migrator to version app {migrator.app_version}")
                migrator.migrate()
                log.success(f"Successfully ran migrator to version app {migrator.app_version}")

    def get_ordered_migrators(self) -> list[Migrator]:
        return sorted(self.migrators, key=lambda migrator: migrator.parsed_app_version)