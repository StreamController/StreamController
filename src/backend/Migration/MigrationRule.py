from abc import ABC, abstractmethod
from copy import deepcopy

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
        pass

    @staticmethod
    def _set_nested(data, path, value):
        pass

    @staticmethod
    def _delete_nested(data, path):
        pass

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