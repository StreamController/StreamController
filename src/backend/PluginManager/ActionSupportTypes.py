class TypeSupport:
    NONE = 0
    UNTESTED = 1
    FULL = 2

class ActionSupports:
    class Keys(TypeSupport):
        pass
    class Dials(TypeSupport):
        pass
    class Touch(TypeSupport):
        pass