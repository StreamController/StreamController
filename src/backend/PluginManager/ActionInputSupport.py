import enum


class ActionInputSupportStatus:
    def __init__(self, num):
        self.num = num

    def __int__(self) -> int:
        return self.num


class ActionInputSupport(enum.Enum):
    NO = ActionInputSupportStatus(0)
    UNTESTED = ActionInputSupportStatus(1)
    SUPPORTED = ActionInputSupportStatus(2)

    def __lt__(self, other):
        if not isinstance(other, ActionInputSupport):
            return TypeError(f"Can't compare {type(self)} with {type(other)}")
        return int(self.value) < int(other.value)
    
    def __gt__(self, other):
        if not isinstance(other, ActionInputSupport):
            return TypeError(f"Can't compare {type(self)} with {type(other)}")
        return int(self.value) > int(other.value)
    
    def __le__(self, other):
        if not isinstance(other, ActionInputSupport):
            return TypeError(f"Can't compare {type(self)} with {type(other)}")
        return int(self.value) <= int(other.value)
    
    def __ge__(self, other):
        if not isinstance(other, ActionInputSupport):
            return TypeError(f"Can't compare {type(self)} with {type(other)}")
        return int(self.value) >= int(other.value)
    
    def __eq__(self, other):
        if not isinstance(other, ActionInputSupport):
            return TypeError(f"Can't compare {type(self)} with {type(other)}")
        return int(self.value) == int(other.value)