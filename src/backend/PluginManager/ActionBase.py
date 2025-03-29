from typing_extensions import deprecated

from src.backend.PluginManager.EventAssigner import EventAssigner
from src.backend.DeckManagement.InputIdentifier import Input, InputEvent
from src.backend.PluginManager.ActionCore import ActionCore

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from src.backend.DeckManagement.DeckController import DeckController
    from src.backend.DeckManagement.InputIdentifier import InputIdentifier
    from src.backend.PageManagement.Page import Page
    from src.backend.PluginManager.PluginBase import PluginBase

@deprecated("This has been deprecated in favor of ActionCore.")
class ActionBase(ActionCore):
    def __init__(self, action_id: str, action_name: str,
                 deck_controller: "DeckController", page: "Page", plugin_base: "PluginBase", state: int,
                 input_ident: "InputIdentifier"):
        super().__init__(action_id, action_name, deck_controller, page, plugin_base, state, input_ident)

        # backward compatibility
        # Key event assigners
        self.add_event_assigner(EventAssigner(
            id="Key Down",
            ui_label="Key Down",
            default_event=Input.Key.Events.DOWN,
            callback=lambda data: self.event_callback(Input.Key.Events.DOWN, data)
        ))
        self.add_event_assigner(EventAssigner(
            id="Key Up",
            ui_label="Key Up",
            default_event=Input.Key.Events.UP,
            callback=lambda data: self.event_callback(Input.Key.Events.UP, data)
        ))
        self.add_event_assigner(EventAssigner(
            id="Key Short Up",
            ui_label="Key Short Up",
            default_event=Input.Key.Events.SHORT_UP,
            callback=lambda data: self.event_callback(Input.Key.Events.SHORT_UP, data)
        ))
        self.add_event_assigner(EventAssigner(
            id="Key Hold Start",
            ui_label="Key Hold Start",
            default_event=Input.Key.Events.HOLD_START,
            callback=lambda data: self.event_callback(Input.Key.Events.HOLD_START, data)
        ))
        self.add_event_assigner(EventAssigner(
            id="Key Hold Stop",
            ui_label="Key Hold Stop",
            default_event=Input.Key.Events.HOLD_STOP,
            callback=lambda data: self.event_callback(Input.Key.Events.HOLD_STOP, data)
        ))

        # Dial event assigners
        self.add_event_assigner(EventAssigner(
            id="Dial Down",
            ui_label="Dial Down",
            default_event=Input.Dial.Events.DOWN,
            callback=lambda data: self.event_callback(Input.Dial.Events.DOWN, data)
        ))
        self.add_event_assigner(EventAssigner(
            id="Dial Up",
            ui_label="Dial Up",
            default_event=Input.Dial.Events.UP,
            callback=lambda data: self.event_callback(Input.Dial.Events.UP, data)
        ))
        self.add_event_assigner(EventAssigner(
            id="Dial Short Up",
            ui_label="Dial Short Up",
            default_event=Input.Dial.Events.SHORT_UP,
            callback=lambda data: self.event_callback(Input.Dial.Events.SHORT_UP, data)
        ))
        self.add_event_assigner(EventAssigner(
            id="Dial Hold Start",
            ui_label="Dial Hold Start",
            default_event=Input.Dial.Events.HOLD_START,
            callback=lambda data: self.event_callback(Input.Dial.Events.HOLD_START, data)
        ))
        self.add_event_assigner(EventAssigner(
            id="Dial Hold Stop",
            ui_label="Dial Hold Stop",
            default_event=Input.Dial.Events.HOLD_STOP,
            callback=lambda data: self.event_callback(Input.Dial.Events.HOLD_STOP, data)
        ))
        self.add_event_assigner(EventAssigner(
            id="Dial Turn CW",
            ui_label="Dial Turn CW",
            default_event=Input.Dial.Events.TURN_CW,
            callback=lambda data: self.event_callback(Input.Dial.Events.TURN_CW, data)
        ))
        self.add_event_assigner(EventAssigner(
            id="Dial Turn CCW",
            ui_label="Dial Turn CCW",
            default_event=Input.Dial.Events.TURN_CCW,
            callback=lambda data: self.event_callback(Input.Dial.Events.TURN_CCW, data)
        ))
        self.add_event_assigner(EventAssigner(
            id="Dial Touchscreen Short Press",
            ui_label="Dial Touchscreen Short Press",
            default_event=Input.Dial.Events.SHORT_TOUCH_PRESS,
            callback=lambda data: self.event_callback(Input.Dial.Events.SHORT_TOUCH_PRESS, data)
        ))
        self.add_event_assigner(EventAssigner(
            id="Dial Touchscreen Long Press",
            ui_label="Dial Touchscreen Long Press",
            default_event=Input.Dial.Events.LONG_TOUCH_PRESS,
            callback=lambda data: self.event_callback(Input.Dial.Events.LONG_TOUCH_PRESS, data)
        ))

        # Touchscreen event assigners
        self.add_event_assigner(EventAssigner(
            id="Touchscreen Drag Left",
            ui_label="Touchscreen Drag Left",
            default_event=Input.Touchscreen.Events.DRAG_LEFT,
            callback=lambda data: self.event_callback(Input.Touchscreen.Events.DRAG_LEFT, data)
        ))
        self.add_event_assigner(EventAssigner(
            id="Touchscreen Drag Right",
            ui_label="Touchscreen Drag Right",
            default_event=Input.Touchscreen.Events.DRAG_RIGHT,
            callback=lambda data: self.event_callback(Input.Touchscreen.Events.DRAG_RIGHT, data)
        ))



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

    def on_key_down(self):
        pass

    def on_key_up(self):
        pass
