from src.backend.PluginManager.ActionBase import ActionBase
from src.backend.PluginManager.PluginBase import PluginBase

class Output(ActionBase):
    ACTION_NAME = "Pause"
    def __init__(self):
        super().__init__()

class Test(PluginBase):
    PLUGIN_NAME = "MediaPlugin"
    GITHUB_REPO = "https://github.com/your-github-repo"
    def __init__(self):
        super().__init__()

        self.add_action(Output)