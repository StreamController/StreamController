from src.backend.DeckManagement.InputIdentifier import Input, InputEvent
from src.backend.PluginManager.EventAssigner import EventAssigner


class EventManager:
    def __init__(self):
        self._event_assigners: list[EventAssigner] = []

        self._overrides: dict[str, str] = {} # {"key_down": "event_1"}

    def set_overrides(self, overrides: dict[str, str]):
        self._overrides = overrides

    def add_event_assigner(self, event_assigner: EventAssigner):
        if self.get_event_assigner_by_id(event_assigner.id):
            raise ValueError(f"Event assigner with id '{event_assigner.id}' already exists on this action")
        self._event_assigners.append(event_assigner)

    def get_all_event_assigners(self) -> list[EventAssigner]:
        return self._event_assigners

    def get_event_assigner_by_id(self, id: str) -> EventAssigner | None:
        for event_assigner in self._event_assigners:
            if event_assigner.id == id:
                return event_assigner

    def get_event_map(self) -> dict[InputEvent, EventAssigner]:
        event_map: dict[InputEvent, EventAssigner] = {}

        all_events = Input.AllEvents()
        for event in all_events:
            event_map[event] = None

        # Assign default events
        for event_assigner in self._event_assigners:
            event_map[event_assigner.default_event] = event_assigner

        # Apply the overrides
        for input_event_str, event_id in self._overrides.items():
            input_event = Input.EventFromStringName(input_event_str)
            event_assigner = self.get_event_assigner_by_id(event_id) if event_id else None
            event_map[input_event] = event_assigner

        return event_map




        return
        event_map: dict[EventAssigner, InputEvent] = {}

        # Assign default events
        for event_assigner in self._event_assigners:
            event_map[event_assigner] = event_assigner.default_event

        for input_event_str, event_id in self._overrides.items():
            input_event = Input.EventFromStringName(input_event_str)
            event_assigner = self.get_event_assigner_by_id(event_id) if event_id else None
            event_map[event_assigner] = input_event

        # Swap keys and values
        event_map = {v: k for k, v in event_map.items()}

        return event_map
    
    def get_event_assigner_for_event(self, event: InputEvent) -> EventAssigner | None:
        return self.get_event_map().get(event)