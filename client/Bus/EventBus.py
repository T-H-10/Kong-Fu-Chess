from typing import Callable, Dict, List, Any

class Event:
    def __init__(self, name: str, data: dict):
        self.name = name
        self.data = data

class EventBus:
    def __init__(self):
        self.subscribers: Dict[str, List[Callable[[Event], None]]] = {}

    def subscribe(self, event_name: str, handler: Callable[[Event], None]):
        if event_name not in self.subscribers:
            self.subscribers[event_name] = []
        self.subscribers[event_name].append(handler)

    def publish(self, event_name: str, data: dict):
        event = Event(event_name, data)
        for handler in self.subscribers.get(event_name, []):
            handler(event)

event_bus = EventBus()