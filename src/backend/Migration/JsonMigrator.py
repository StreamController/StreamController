from src.backend.Migration.MigrationBase import MigrationBase
from abc import ABC, abstractmethod
from copy import deepcopy
import json
from typing import List, Callable
from packaging.version import Version

class MigrationException(Exception):
    pass

class MigrationRule(ABC):
    def __init__(self, source: str, destination: str = None):
        self.source = source
        self.destination = destination

    @abstractmethod
    def apply(self, data):
        pass

    @staticmethod
    def _get_nested(data, path):
        """Retrieve a value from a nested dictionary using a dot-separated path."""
        try:
            keys = path.split(".")
            for key in keys:
                data = data[key]
            return data
        except Exception as e:
            raise MigrationException(f"Error while getting nested dictionary! {e}")

    @staticmethod
    def _set_nested(data, path, value):
        """Set a value in a nested dictionary using a dot-separated path."""
        try:
            keys = path.split(".")
            for key in keys[:-1]:
                data = data.setdefault(key, {})
            data[keys[-1]] = value
        except Exception as e:
            raise MigrationException(f"Error while setting nested dictionary! {e}")

    @staticmethod
    def _delete_nested(data, path):
        """Delete a value in a nested dictionary using a dot-separated path."""
        try:
            keys = path.split(".")
            for key in keys[:-1]:
                data = data[key]
            del data[keys[-1]]
        except Exception as e:
            raise MigrationException(f"Error while deleting nested dictionary! {e}")

    @staticmethod
    def _copy_data(data):
        return deepcopy(data)

    @staticmethod
    def copy_data(func):
        def wrapper(self, data, *args, **kwargs):
            copied_data = MigrationRule._copy_data(data)
            try:
                func(self, copied_data, *args, **kwargs)
                data.clear()
                data.update(copied_data)
            except Exception as e:
                print(e)
        return wrapper

class MoveRule(MigrationRule):
    @MigrationRule.copy_data
    def apply(self, data):
        value = MoveRule._get_nested(data, self.source)
        MoveRule._set_nested(data, self.destination, value)
        MoveRule._delete_nested(data, self.source)

class DeleteRule(MigrationRule):
    @MigrationRule.copy_data
    def apply(self, data):
        # Delete the value at the source path
        DeleteRule._delete_nested(data, self.source)

class JsonMigrator(MigrationBase):
    def __init__(self, migration_file_path: str, from_version: str, to_version: str,
                 version_conditions: List[Callable[[Version, Version], bool]] = None) -> None:
        super().__init__(migration_file_path, from_version, to_version, version_conditions)

    def migrate(self, migration_rules: list[MigrationRule]):
        if not self.validate_version():
            return

        file = self.read_file()
        json_data = json.loads(file)

        for rule in migration_rules:
            rule.apply(json_data)

        return json_data