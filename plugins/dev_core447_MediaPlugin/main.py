from src.backend.PluginManager.ActionBase import ActionBase
from src.backend.PluginManager.PluginBase import PluginBase

class Output(ActionBase):
    ACTION_NAME = "Pause"
    def __init__(self, deck_controller, page, coords):
        super().__init__(deck_controller=deck_controller, page=page, coords=coords)

    def on_key_down(self):
        print("down")
        print(f"controller: {self.deck_controller}")

    def on_key_up(self):
        print("up")
        print(f"controller: {self.deck_controller}")

class Test(PluginBase):
    PLUGIN_NAME = "MediaPlugin"
    GITHUB_REPO = "https://github.com/your-github-repo"
    def __init__(self):
        super().__init__()

        self.add_action(Output)