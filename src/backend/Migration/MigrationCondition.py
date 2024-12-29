from abc import abstractmethod

class MigrationCondition:
    @abstractmethod
    def check(self) -> bool:
        pass