from ..CustomLogger import CustomLogger

class MigrationLogger(CustomLogger):
    TRACE: str = "MIGRATION_TRACE"
    DEBUG: str = "MIGRATION_DEBUG"
    INFO: str = "MIGRATION_INFO"
    SUCCESS: str = "MIGRATION_SUCCESS"
    WARNING: str = "MIGRATION_WARNING"
    ERROR: str = "MIGRATION_ERROR"
    CRITICAL: str = "MIGRATION_CRITICAL"
    FILTER: str = "MIGRATION"

    def __init__(self, colors: dict[str, str] = None):
        super().__init__(colors)

migration_logger = MigrationLogger()