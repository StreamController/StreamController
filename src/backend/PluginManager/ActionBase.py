from src.backend.DeckManagement.InputIdentifier import Input, InputEvent
from src.backend.PluginManager.ActionCore import ActionCore

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from src.backend.DeckManagement.DeckController import DeckController
    from src.backend.DeckManagement.InputIdentifier import InputIdentifier
    from src.backend.PageManagement.Page import Page
    from src.backend.PluginManager.PluginBase import PluginBase

class ActionBase(ActionCore):
    def __init__(self, action_id: str, action_name: str,
                 deck_controller: "DeckController", page: "Page", plugin_base: "PluginBase", state: int,
                 input_ident: "InputIdentifier"):
        super().__init__(action_id, action_name, deck_controller, page, plugin_base, state, input_ident)

        # backward compatibility
        self.add_event_assigner(
            Input.Key.Events.DOWN,
            lambda data: self.event_callback(Input.Key.Events.DOWN, data)
        )
        self.add_event_assigner(
            Input.Key.Events.UP,
            lambda data: self.event_callback(Input.Key.Events.UP, data)
        )
        self.add_event_assigner(
            Input.Dial.Events.DOWN,
            lambda data: self.event_callback(Input.Dial.Events.DOWN, data)
        )
        self.add_event_assigner(
            Input.Dial.Events.UP,
            lambda data: self.event_callback(Input.Dial.Events.UP, data)
        )
        self.add_event_assigner(
            Input.Dial.Events.SHORT_TOUCH_PRESS,
            lambda data: self.event_callback(Input.Dial.Events.SHORT_TOUCH_PRESS, data)
        )

    # backward compatibility
    def event_callback(self, event: InputEvent, data: dict = None):
        ## backward compatibility
        if event == Input.Key.Events.DOWN:
            self.on_key_down()
        elif event == Input.Key.Events.UP:
            self.on_key_up()
        elif event == Input.Dial.Events.DOWN:
            self.on_key_down()
        elif event == Input.Dial.Events.UP:
            self.on_key_up()
        elif event == Input.Dial.Events.SHORT_TOUCH_PRESS:
            self.on_key_down()

    def on_key_down(self):
        pass

    def on_key_up(self):
        pass