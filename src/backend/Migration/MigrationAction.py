from abc import ABC


class MigrationAction(ABC):
    def __init__(self, source: list[str], destination: list[str] = None):
        self.source: list[str] = source
        self.destination: list[str] = destination