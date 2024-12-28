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
from src.backend.Migration.MigrationBase import MigrationBase

from loguru import logger as log

class MigrationManager:
    def __init__(self):
        self.base_migrators: list[MigrationBase] = []

    def add_base_migrator(self, migrator: MigrationBase):
        self.base_migrators.append(migrator)

    def run_migration(self):
        for migrator in self.base_migrators:
            migrator.migrate()