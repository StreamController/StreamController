import fnmatch
from typing import Callable, Dict, Any, List

from src.backend.Migration.MigrationAction import MigrationAction
from abc import ABC, abstractmethod
from copy import deepcopy
from loguru import logger as log

class JsonAction(MigrationAction, ABC):
    def __init__(self, source: list[str], destination: list[str] = None):
        super().__init__(source, destination)

    @staticmethod
    def copy_data(func):
        def wrapper(self, data, *args, **kwargs):
            copied_data = self._copy_data(data)
            try:
                if func(self, copied_data, *args, **kwargs):
                    data.clear()
                    data.update(copied_data)
                    return True
                return False
            except Exception as e:
                log.log("MIGRATION_ERRRO", f"FAILED COPYING AND APPLYING DATA {data}: {e}")
                return False
        return wrapper

    @copy_data
    @abstractmethod
    def apply(self, data) -> bool:
        pass

    def _copy_data(self, data):
        return deepcopy(data)

    def dict_to_paths(self, data: Dict[str, Any], parent_key: List[str] = None) -> List[List[str]]:
        """
        Convert a dictionary into a list of paths, represented as lists of keys.

        :param data: The dictionary to convert.
        :param parent_key: The current path as a list of keys.
        :return: A list of paths (each path is a list of keys).
        """
        paths = []
        if parent_key is None:
            parent_key = []
        for key, value in data.items():
            full_key = parent_key + [key]
            if isinstance(value, dict):
                paths.extend(self.dict_to_paths(value, full_key))  # Recurse into sub-dictionaries
            else:
                paths.append(full_key)
        return paths

    def _get_nested(self, data, keys: List[str]):
        """Helper function to traverse the dictionary."""
        for key in keys:
            if isinstance(data, dict):
                if key == '*':  # Handle wildcard
                    return {
                        k: self._get_nested(data[k], keys[1:]) if isinstance(data[k], dict) else data[
                            k] for k in data}
                data = data.get(key, None)
                if data is None:
                    return None
            else:
                return None
        return data

    def get_nested(self, data: Dict[str, Any], path: List[str]):
        """Returns nested value based on path, supports wildcards."""
        return self._get_nested(data, path)

    def _set_nested(self, data, keys: List[str], value: Any):
        """Helper function to traverse and set the value."""
        for key in keys[:-1]:
            if key == '*':
                for k in data.keys():
                    self._set_nested(data[k], keys[1:], value)
                return
            if key not in data or not isinstance(data[key], dict):
                data[key] = {}
            data = data[key]
        last_key = keys[-1]
        if last_key == '*':  # Handle wildcard and replace all sub-values
            for k in data.keys():
                data[k] = value
        else:
            data[last_key] = value

    def set_nested(self, data: Dict[str, Any], path: List[str], value: Any):
        """Sets the nested value based on path, supports wildcards for deletion."""
        self._set_nested(data, path, value)

    def _delete_nested(self, data, keys: List[str]):
        """Helper function to traverse and delete the value."""
        for key in keys[:-1]:
            if key == '*':  # Wildcard handling
                for k in list(data.keys()):
                    JsonAction._delete_nested(data[k], keys[1:])
                return
            if key not in data or not isinstance(data[key], dict):
                return
            data = data[key]
        last_key = keys[-1]
        if last_key == '*':  # Handle wildcard for full deletion
            data.clear()
        elif last_key in data:
            del data[last_key]

    def delete_nested(self, data: Dict[str, Any], path: List[str]):
        """Deletes nested structure based on path, supports wildcards."""
        self._delete_nested(data, path)