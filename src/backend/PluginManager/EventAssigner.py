from src.backend.DeckManagement.InputIdentifier import InputEvent

class EventAssigner:
    def __init__(self, id: str, ui_label: str, callback: callable, default_events: list[InputEvent] = None, default_event: InputEvent = None, tooltip: str = None):
        self.id = id
        self.ui_label = ui_label
        self.default_events = default_events if default_events else [default_event]
        self.callback = callback
        self.tooltip = tooltip

    def call(self, *args, **kwargs):
        self.callback(*args, **kwargs)