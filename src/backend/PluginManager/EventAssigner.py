from src.backend.DeckManagement.InputIdentifier import InputEvent

class EventAssigner:
    def __init__(self, id: str, ui_label: str, default_event: InputEvent, callback: callable):
        self.id = id
        self.ui_label = ui_label
        self.default_event = default_event
        self.callback = callback

    def call(self, *args, **kwargs):
        self.callback(*args, **kwargs)