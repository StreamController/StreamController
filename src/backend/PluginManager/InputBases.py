from abc import ABC

from backend.PluginManager.ActionCore import ActionCore

class InputAction(ABC):
    pass

class KeyAction(InputAction):
    pass



###### Usage example

class VolumeAction(ActionCore):
    def increase():
        print("Volume increased")

    def on_trigger(self, *args, **kwargs):
        self.increase()


class KeyVolumeAction(KeyAction, VolumeAction):
    def __init__(self, action_id: str, action_name: str,
                 deck_controller: "DeckController", page: "Page", plugin_base: "PluginBase", state: int,
                 input_ident: "InputIdentifier"):
        super().__init__(action_id, action_name, deck_controller, page, plugin_base, state, input_ident)


        self.add_event_assigner(
            Input.Key.Events.DOWN,
            self.on_trigger()
        )