class InputIdentifier:
    def __init__(self, input_type: str, input_identifier: str, controller_class_name: str):
        self.input_type = input_type
        self.input_identifier = input_identifier
        self.controller_class_name = controller_class_name
    def get_config(self, d):
        self.get_dict(d)
        d[self.input_type][self.input_identifier].setdefault("states", {})
        return d[self.input_type][self.input_identifier]
    def get_dict(self, d):
        d.setdefault(self.input_type, {})
        d[self.input_type].setdefault(self.input_identifier, {})
        return d[self.input_type][self.input_identifier]
    def __eq__(self, o):
        if not isinstance(o, InputIdentifier):
            raise ValueError("Invalid type")
        return self.input_type == o.input_type and self.input_identifier == o.input_identifier
    def __str__(self):
        return f"Input({self.input_type}, {self.input_identifier})"

class Input:
    class Key(InputIdentifier):
        def __init__(self, identifier: str):
            super().__init__("keys", identifier, "ControllerKey")
    class Dial(InputIdentifier):
        def __init__(self, identifier: str):
            super().__init__("dials", identifier, "ControllerDial")
    class Touchscreen(InputIdentifier):
        def __init__(self, identifier: str):
            super().__init__("touchscreens", identifier, "ControllerTouchScreen")
    All = ()
    def FromTypeIdentifier(input_type: str, input_identifier: str):
        if input_type == "keys":
            return Input.Key(input_identifier)
        if input_type == "dials":
            return Input.Dial(input_identifier)
        if input_type == "touchscreens":
            return Input.Touchscreen(input_identifier)
        raise ValueError(f"Unknown input type {input_type}")
Input.All = (Input.Key(None), Input.Dial(None), Input.Touchscreen(None))
