from typing import Callable
from packaging.version import Version
from packaging import version

from src.backend.Migration.MigrationCondition import MigrationCondition

class VersionCondition(MigrationCondition):
    def __init__(self, from_version: str, to_version: str, condition: Callable[[Version, Version], bool]):
        self.from_version: Version = version.parse(from_version)
        self.to_version: Version = version.parse(to_version)
        self.condition: Callable[[Version, Version], bool] = condition

    def check(self) -> bool:
        return self.condition(self.from_version, self.to_version)