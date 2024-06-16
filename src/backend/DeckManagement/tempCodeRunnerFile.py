from enum import Enum

class InputEvent(Enum):
    def __new__(cls, string_name):
        obj = object.__new__(cls)
        obj._value_ = len(cls.__members__)  # Auto-incremented value
        obj.string_name = string_name
        return obj

class Input:
    class Key:
        class Events(InputEvent):
            UP = "Key UP"
            DOWN = "Key DOWN"

    class Dial:
        class Events(InputEvent):
            TURN_CW = "Dial Turn Clockwise"
            TURN_CCW = "Dial Turn Counter-Clockwise"
    
    @staticmethod
    def all_events():
        events = []
        for attr in dir(Input):
            nested_class = getattr(Input, attr, None)
            if isinstance(nested_class, type):
                for sub_attr in dir(nested_class):
                    sub_nested_class = getattr(nested_class, sub_attr, None)
                    if isinstance(sub_nested_class, type) and issubclass(sub_nested_class, Enum):
                        events.extend(list(sub_nested_class))
        return events

# Example usage
event = Input.Key.Events.UP

# Comparison
print(event == Input.Key.Events.UP)  # Output: True

# Get the string name of the enum member
print(Input.Key.Events.UP.string_name)  # Output: Key UP
print(Input.Dial.Events.TURN_CW.string_name)  # Output: Dial Turn Clockwise

# Print the enum member's name
print(Input.Key.Events.UP.name)  # Output: UP

# Get all available events
print("-------------------")
all_events = Input.all_events()
for evt in all_events:
    print(f"{evt.name}: {evt.string_name}")

# Output:
# UP: Key UP
# DOWN: Key DOWN
# TURN_CW: Dial Turn Clockwise
# TURN_CCW: Dial Turn Counter-Clockwise
