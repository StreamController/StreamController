from ..MigrationRule import MigrationRule, MigrationException
from abc import ABC, abstractmethod

class JsonMigrationRule(MigrationRule):
    def __init__(self, source: str, destination: str = None):
        super().__init__(source, destination)

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

class MoveRule(JsonMigrationRule):
    @MigrationRule.copy_data
    def apply(self, data):
        value = MoveRule._get_nested(data, self.source)
        MoveRule._set_nested(data, self.destination, value)
        MoveRule._delete_nested(data, self.source)

class DeleteRule(JsonMigrationRule):
    @MigrationRule.copy_data
    def apply(self, data):
        # Delete the value at the source path
        DeleteRule._delete_nested(data, self.source)