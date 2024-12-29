from src.backend.Migration.JsonMigrator.JsonAction import JsonAction
from src.backend.Migration.JsonMigrator.JsonMigrator import JsonMigrator
from src.backend.Migration.MigrationActions.JsonActions import MoveAction, DeleteAction
import json

class Settings_1_5_0_b8(JsonMigrator):
    def __init__(self,
                 dependant_migrator: "MigrationBase" = None,
                 ignore_backup_success: bool = False):
        migration_actions: list[JsonAction] = [MoveAction(["*"], ["settings"]),
                                               DeleteAction(["settings", "1.5.0"])]
        migration_conditions = []

        super().__init__(migration_actions, migration_conditions, dependant_migrator, ignore_backup_success)

    def _migrate(self) -> bool:
        json_data: dict = {}
        with open("/home/gapls/Documents/programming/python/StreamController/Envs/StreamController-main/data/settings/migrations.json", "r") as file:
            json_data = json.load(file)

        print("JSON MIGRATION")
        for action in self.migration_actions:
            action.apply(json_data)

        print(json_data)

        return True