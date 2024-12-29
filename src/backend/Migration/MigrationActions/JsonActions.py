from src.backend.Migration.JsonMigrator.JsonAction import JsonAction

class MoveAction(JsonAction):
    def __init__(self, source: list[str], destination: list[str] = None):
        """Accepts wildcard in source"""
        super().__init__(source, destination)

    @JsonAction.copy_data
    def apply(self, data):
        value = self._get_nested(data, self.source)
        self.delete_nested(data, self.source)
        self.set_nested(data, self.destination, value)

class DeleteAction(JsonAction):
    def __init__(self, source: list[str]):
        """Accepts wildcard in source"""
        super().__init__(source)

    def apply(self, data):
        # Delete the value at the source path
        self.delete_nested(data, self.source)