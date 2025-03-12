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
                callback=self.on_key_down
            ))
            self.add_event_assigner(EventAssigner(
                id="Key Up",
                ui_label="Key Up",
                default_event=Input.Key.Events.UP,
                callback=self.on_key_up
            ))
            self.add_event_assigner(EventAssigner(
                id="Key Short Up",
                ui_label="Key Short Up",
                default_event=Input.Key.Events.SHORT_UP,
                callback=self.on_key_short_up
            ))
            self.add_event_assigner(EventAssigner(
                id="Key Hold Start",
                ui_label="Key Hold Start",
                default_event=Input.Key.Events.HOLD_START,
                callback=self.on_key_hold_start
            ))
            self.add_event_assigner(EventAssigner(
                id="Key Hold Stop",
                ui_label="Key Hold Stop",
                default_event=Input.Key.Events.HOLD_STOP,
                callback=self.on_key_hold_stop
            ))

    def on_key_down(self):
        pass
        
    def on_key_up(self):
        pass
        
    def on_key_short_up(self):
        pass
        
    def on_key_hold_start(self):
        pass
        
    def on_key_hold_stop(self):
        pass

class DialAction(InputAction, ActionCore):
    def __init__(self, default_events: bool = True, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if default_events:
            self.add_event_assigner(EventAssigner(
                id="Dial Down",
                ui_label="Dial Down",
                default_event=Input.Dial.Events.DOWN,
                callback=self.on_dial_down
            ))
            self.add_event_assigner(EventAssigner(
                id="Dial Up",
                ui_label="Dial Up",
                default_event=Input.Dial.Events.UP,
                callback=self.on_dial_up
            ))
            self.add_event_assigner(EventAssigner(
                id="Dial Short Up",
                ui_label="Dial Short Up",
                default_event=Input.Dial.Events.SHORT_UP,
                callback=self.on_dial_short_up
            ))
            self.add_event_assigner(EventAssigner(
                id="Dial Hold Start",
                ui_label="Dial Hold Start",
                default_event=Input.Dial.Events.HOLD_START,
                callback=self.on_dial_hold_start
            ))
            self.add_event_assigner(EventAssigner(
                id="Dial Hold Stop",
                ui_label="Dial Hold Stop",
                default_event=Input.Dial.Events.HOLD_STOP,
                callback=self.on_dial_hold_stop
            ))
            self.add_event_assigner(EventAssigner(
                id="Dial Turn CW",
                ui_label="Dial Turn CW",
                default_event=Input.Dial.Events.TURN_CW,
                callback=self.on_dial_turn_cw
            ))
            self.add_event_assigner(EventAssigner(
                id="Dial Turn CCW",
                ui_label="Dial Turn CCW",
                default_event=Input.Dial.Events.TURN_CCW,
                callback=self.on_dial_turn_ccw
            ))
            self.add_event_assigner(EventAssigner(
                id="Dial Touchscreen Short Press",
                ui_label="Dial Touchscreen Short Press",
                default_event=Input.Dial.Events.SHORT_TOUCH_PRESS,
                callback=self.on_dial_short_touch_press
            ))
            self.add_event_assigner(EventAssigner(
                id="Dial Touchscreen Long Press",
                ui_label="Dial Touchscreen Long Press",
                default_event=Input.Dial.Events.LONG_TOUCH_PRESS,
                callback=self.on_dial_long_touch_press
            ))

    def on_dial_down(self):
        pass
        
    def on_dial_up(self):
        pass
        
    def on_dial_short_up(self):
        pass
        
    def on_dial_hold_start(self):
        pass
        
    def on_dial_hold_stop(self):
        pass
        
    def on_dial_turn_cw(self):
        pass
        
    def on_dial_turn_ccw(self):
        pass
        
    def on_dial_short_touch_press(self):
        pass
        
    def on_dial_long_touch_press(self):
        pass

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
                callback=self.on_touchscreen_drag_right
            ))

    def on_touchscreen_drag_left(self):
        pass
        
    def on_touchscreen_drag_right(self):
        pass


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