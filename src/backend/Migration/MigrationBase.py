import os
from abc import ABC, abstractmethod
from typing import List, Tuple, Callable

from packaging import version
from packaging.version import Version
import operator

def version_checker(version: Version, conditions: List[Tuple[Callable[[Version, Version], bool], Version]]) -> bool:
    """
    Generalized function to check a version against multiple conditions.

    Args:
        version (Version): The version to check.
        conditions (List[Tuple[Callable[[Version, Version], bool], Version]]):
            A list of conditions. Each condition is a tuple where:
                - The first element is a callable that takes two Versions and returns a bool.
                - The second element is a Version instance to compare against.

    Returns:
        bool: True if all conditions are satisfied, False otherwise.

    Example:
        >>> import operator
        >>> from packaging.version import Version
        >>> conditions = [
        ...     (operator.ge, Version("1.0.0")),   # Version >= 1.0.0
        ...     (operator.lt, Version("2.0.0")),   # Version < 2.0.0
        ...     (operator.ne, Version("1.5.0")),   # Version != 1.5.0
        ... ]
        >>> version_checker(Version("1.5.0.beta.7"), conditions)
        True

        >>> version_checker(Version("1.5.0"), conditions)
        False
    """
    return all(comparator(version, bound) for comparator, bound in conditions)

class MigrationBase(ABC):
    def __init__(self, migration_file_path: str, from_version: str, to_version: str,
                 version_conditions: List[Callable[[Version, Version], bool]],
                 depends_on: "MigrationBase" = None) -> None:
        """
        The MigrationBase is used for all Migrators.

        Args:
            migration_file_path (str): The path to the migration file.
            from_version (str): The version to compare against.
            to_version (str): The version to compare against.
            version_conditions (List[Callable[[Version, Version], bool]]): A list of conditions. The from_version will always be compared to the to_version and it will always contain a from_version < to_version check.

        Example:
            >>> import operator
            >>> migrator = MigrationBase("~/.config/StreamController/test.json", "1.0.0.beta.5", "1.0.0", [operator.ne])
        """
        self.migration_file_path: str = migration_file_path
        self.migration_from: Version = version.parse(from_version)
        self.migration_to: Version = version.parse(to_version)
        self.migration_version_conditions: List[Callable[[Version, Version], bool]] = [operator.lt] + version_conditions
        self.dependant_migration: "MigrationBase" = depends_on

        self.migration_ran: bool = False

    # Migration Methods

    @abstractmethod
    def migrate(self, *args, **kwargs):
        pass

    def validate_migration(self):
        pass

    # Version Checking

    def validate_version(self) -> bool:
        conditions: List[Tuple[Callable[[Version, Version], bool], Version]] = []

        for migration_condition in self.migration_version_conditions:
            conditions.append((migration_condition, self.migration_to))

        version_checks = version_checker(self.migration_from, conditions)
        self.migration_ran = version_checks

        return version_checks

    # File Writers

    def write_file(self, data) -> bool:
        if os.path.isdir(self.migration_file_path):
            return False

        try:
            with open(self.migration_file_path, "w") as f:
                f.write(data)
            return True
        except:
            return False

    def read_file(self) -> str:
        if os.path.isfile(self.migration_file_path):
            with open(self.migration_file_path, "r") as file:
                return file.read()
        return None

    def backup(self):
        pass