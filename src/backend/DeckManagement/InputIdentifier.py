from typing import TYPE_CHECKING
import enum

if TYPE_CHECKING:
    from src.backend.PageManagement.Page import Page
    from src.backend.DeckManagement.DeckController import DeckController, ControllerInput


class InputIdentifier:
    def __init__(self, input_type: str, json_identifier: str, controller_class_name: str):
        self.input_type = input_type
        self.json_identifier: str = json_identifier
        self.controller_class_name = controller_class_name

    def get_config(self, page: "Page") -> dict:
        return page.dict.get(self.input_type, {}).get(self.json_identifier, {})

    def get_dict(self, d):
        d.setdefault(self.input_type, {})
        d[self.input_type].setdefault(self.json_identifier, {})
        return d[self.input_type][self.json_identifier]
    
    def get_controller_input(self, controller: "DeckController") -> "ControllerInput":
        return controller.get_input(self)
    
    def __eq__(self, o):
        if o is None:
            return False
        if not isinstance(o, InputIdentifier):
            raise ValueError(f"Invalid type {type(o)} for InputIdentifier")
        return self.input_type == o.input_type and self.json_identifier == o.json_identifier

    def __str__(self):
        return f"Input({self.input_type}, {self.json_identifier})"

class InputEvent:
    def __init__(self, input_type: str, n: int):
        self.input_type = input_type
        self.n = n

    def __eq__(self, o: "InputEvent"):
        if o is None:
            return False
        if not isinstance(o, InputEvent):
            raise ValueError(f"Invalid type {type(o)} for InputEvent")
        return self.input_type == o.input_type and self.n == o.n


class Input:
    class Key(InputIdentifier):
        input_type = "keys"
        controller_class_name = "ControllerKey"

        class Events(enum.Enum):
            UP = InputEvent("keys", 0)
            DOWN = InputEvent("keys", 1)
            HOLD_START = InputEvent("keys", 2)
            HOLD_UP = InputEvent("keys", 3)

        def __init__(self, json_identifier: str):
            self.coords = Input.Key.Coords_From_PageCoords(json_identifier)
            self.json_identifier = Input.Key.Coords_To_PageCoords(self.coords)
            super().__init__(self.input_type, self.json_identifier, self.controller_class_name)

        @staticmethod
        def Coords_From_PageCoords(page_coords: str):
            split = page_coords.split("x")
            return (int(split[0]), int(split[1]))
        
        @staticmethod
        def Coords_To_PageCoords(coords: tuple[int, int]):
            return f"{coords[0]}x{coords[1]}"
        
        @staticmethod
        def Index_To_Coords(deck_controller: "DeckController", index):
            rows, cols = deck_controller.deck.key_layout()
            x = index % cols
            y = index // cols
            return (x, y)
        
        @staticmethod
        def Coords_To_Index(deck_controller: "DeckController", coords):# -> Any:
            if type(coords) == str:
                coords = coords.split("x")
            x, y = map(int, coords)
            rows, cols = deck_controller.deck.key_layout()
            return y * cols + x
        
        def get_page_coords(self):
            return self.Coords_To_PageCoords(self.coords)
        
        def get_index(self, deck_controller: "DeckController"):
            return self.Coords_To_Index(deck_controller, self.coords)
        
    class Dial(InputIdentifier):
        input_type = "dials"
        controller_class_name = "ControllerDial"
  
        def __init__(self, json_identifier: str):
            self.index = str(json_identifier)
            super().__init__(self.input_type, json_identifier, self.controller_class_name)

    class Touchscreen(InputIdentifier):
        input_type = "touchscreens"
        controller_class_name = "ControllerTouchScreen"

        def __init__(self, json_identifier: str):
            self.index = str(json_identifier)
            super().__init__(self.input_type, json_identifier, self.controller_class_name)

    All = (Key, Dial, Touchscreen)
    KeyTypes = [key_type.input_type for key_type in All]
    
    @staticmethod
    def FromTypeIdentifier(input_type: str, json_identifier: str):
        input_map = {
            "keys": Input.Key,
            "dials": Input.Dial,
            "touchscreens": Input.Touchscreen
        }
        if input_type in input_map:
            return input_map[input_type](json_identifier)
        raise ValueError(f"Unknown input type {input_type}")