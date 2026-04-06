"""
EventBus — Patrón Observer/Publish-Subscribe.
Publica eventos y los despacha a todos los handlers suscritos.
Los handlers reaccionan sin que el emisor sepa quiénes escuchan.
"""
from typing import Callable
from core.events.types import Event


class EventBus:
    """
    Singleton que gestiona suscripciones y publicaciones de eventos.
    Cada handler se suscribe a un tipo de evento por nombre.
    Cuando se publica un evento, todos los handlers suscritos se ejecutan.
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._handlers: dict[str, list[Callable]] = {}
        return cls._instance

    def subscribe(self, event_name: str, handler: Callable[[Event], None]) -> None:
        """Suscribe un handler a un tipo de evento."""
        if event_name not in self._handlers:
            self._handlers[event_name] = []
        self._handlers[event_name].append(handler)

    def publish(self, event: Event) -> None:
        """Publica un evento a todos los handlers suscritos."""
        # Handlers específicos
        for handler in self._handlers.get(event.name, []):
            handler(event)
        # Handlers wildcard (escuchan todo)
        for handler in self._handlers.get("*", []):
            handler(event)

    def reset(self) -> None:
        """Limpia todas las suscripciones (útil para tests)."""
        self._handlers = {}
