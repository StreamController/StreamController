class TypeSupportStatus:
    def __init__(self, num, type):
        self.num = num
        self.type = type
    def __int__(self):
        return self.num

class TypeSupport:
    def __init__(self, type):
        self.type = type
        self.NONE = TypeSupportStatus(0, type)
        self.UNTESTED = TypeSupportStatus(1, type)
        self.FULL = TypeSupportStatus(2, type)

class ActionSupports:
    class Keys(TypeSupport):
        def __init__(self):
            super().__init__("keys")
    class Dials(TypeSupport):
        def __init__(self):
            super().__init__("dials")
    class Touch(TypeSupport):
        def __init__(self):
            super().__init__("touchscreens")