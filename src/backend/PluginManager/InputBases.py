from abc import ABC

from src.backend.PluginManager.EventAssigner import EventAssigner
from src.backend.DeckManagement.InputIdentifier import Input, InputIdentifier
from src.backend.PluginManager.ActionCore import ActionCore

class InputAction(ABC):
    pass

class KeyAction(InputAction, ActionCore):
    def __init__(self, default_events: bool = True, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if default_events:
            self.add_event_assigner(EventAssigner(
                id="Key Down",
                ui_label="Key Down",
                default_event=Input.Key.Events.DOWN,
                callback=self.on_trigger
            ))

class DialAction(InputAction, ActionCore):
    def __init__(self, default_events: bool = True, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if default_events:
            self.add_event_assigner(EventAssigner(
                id="Dial Down",
                ui_label="Dial Down",
                default_event=Input.Dial.Events.DOWN,
                callback=self.on_trigger
            ))


class TouchScreenAction(InputAction, ActionCore):
    def __init__(self, default_events: bool = True, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if default_events:
            self.add_event_assigner(EventAssigner(
                id="Touchscreen Drag Left",
                ui_label="Touchscreen Drag Left",
                default_event=Input.Touchscreen.Events.DRAG_LEFT,
                callback=self.on_trigger
            ))

            self.add_event_assigner(EventAssigner(
                id="Touchscreen Drag Right",
                ui_label="Touchscreen Drag Right",
                default_event=Input.Touchscreen.Events.DRAG_RIGHT,
                callback=self.on_trigger
            ))


###### Usage example

# class VolumeAction(ActionCore):
#     def increase():
#         print("Volume increased")

#     def on_trigger(self, *args, **kwargs):
#         self.increase()


# class KeyVolumeAction(KeyAction, VolumeAction):
#     def __init__(self, action_id: str, action_name: str,
#                  deck_controller: "DeckController", page: "Page", plugin_base: "PluginBase", state: int,
#                  input_ident: "InputIdentifier"):
#         super().__init__(action_id, action_name, deck_controller, page, plugin_base, state, input_ident)


#         self.add_event_assigner(
#             Input.Key.Events.DOWN,
#             self.on_trigger()
#         )