from src.backend.Migration.JsonMigrator.JsonAction import JsonAction
from loguru import logger as log

class MoveAction(JsonAction):
    def __init__(self, source: list[str], destination: list[str] = None):
        """Accepts wildcard in source"""
        super().__init__(source, destination)

    @JsonAction.copy_data
    def apply(self, data) -> bool:
        log.info(f"MOVING {self.source} -> {self.destination}")
        value = self._get_nested(data, self.source)
        self.delete_nested(data, self.source)
        self.set_nested(data, self.destination, value)
        return True

class DeleteAction(JsonAction):
    def __init__(self, source: list[str]):
        """Accepts wildcard in source"""
        super().__init__(source)

    def apply(self, data) -> bool:
        # Delete the value at the source path
        log.info(f"DELETING {self.source}")
        self.delete_nested(data, self.source)
        return True

class AddAction(JsonAction):
    def __init__(self, source: list[str], value: any):
        super().__init__(source)
        self.value = value

    def apply(self, data) -> bool:
        log.info(f"ADDING {self.source} : {self.value}")
        self.set_nested(data, self.source, self.value)
        return True


class CompareAction(JsonAction):
    def __init__(self, source: list[str], value):
        super().__init__(source)
        self.value = value

    def apply(self, data) -> bool:
        value = self.get_nested(data, self.source)
        log.info(f"COMPARING {self.source} ({value}) : {self.value} | RESULT: {value == self.value}")
        return value == self.value