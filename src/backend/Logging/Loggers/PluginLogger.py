from ..CustomLogger import CustomLogger

class PluginLogger(CustomLogger):
    TRACE: str = "PLUGIN_TRACE"
    DEBUG: str = "PLUGIN_DEBUG"
    INFO: str = "PLUGIN_INFO"
    SUCCESS: str = "PLUGIN_SUCCESS"
    WARNING: str = "PLUGIN_WARNING"
    ERROR: str = "PLUGIN_ERROR"
    CRITICAL: str = "PLUGIN_CRITICAL"
    FILTER: str = "PLUGIN"

    def __init__(self, colors: dict[str, str] = None):
        super().__init__(colors)

plugin_logger = PluginLogger()