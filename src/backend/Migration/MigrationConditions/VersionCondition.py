from typing import Callable
from packaging.version import Version
from packaging import version

from src.backend.Migration.MigrationCondition import MigrationCondition
from loguru import logger as log

class VersionCondition(MigrationCondition):
    def __init__(self, from_version: str, to_version: str, condition: Callable[[Version, Version], bool]):
        self.from_version: Version = version.parse(from_version)
        self.to_version: Version = version.parse(to_version)
        self.condition: Callable[[Version, Version], bool] = condition

    def check(self) -> bool:
        log.log("MIGRATION_INFO", f"COMPARING VERSIONS: {self.from_version} -> {self.to_version}")
        success = self.condition(self.from_version, self.to_version)

        if success:
            log.log("MIGRATION_SUCCESS", f"VERSION CHECK SUCCESS: {success}")
        else:
            log.log("MIGRATION_ERROR", f"VERSION CHECK SUCCESS: {success}")
        return success