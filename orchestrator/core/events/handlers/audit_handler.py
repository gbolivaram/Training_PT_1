"""
AuditHandler — Observer que registra TODOS los eventos en history_log.
Se suscribe con wildcard (*) para capturar todo.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from core.events.types import Event
from repositories.history_repository import HistoryRepository


def on_any_event(event: Event):
    """Registra cualquier evento del sistema en history_log."""
    # Extraer campos del evento según su tipo
    node_id = getattr(event, "node_id", "") or getattr(event, "next_node_id", "") or ""
    titulo = event.payload.get("titulo", event.name)
    rol = getattr(event, "rol", "") or event.payload.get("rol", "")
    inputs = event.payload.get("inputs", {})
    decision = getattr(event, "decision", None)
    decision_label = getattr(event, "decision_label", None)

    HistoryRepository.append(
        instance_id=event.instance_id,
        node_id=node_id,
        titulo=titulo,
        rol=rol,
        inputs=inputs,
        decision=decision,
        decision_label=decision_label,
        event_type=event.name,
    )


def register(bus):
    """Registra el audit handler con wildcard."""
    bus.subscribe("*", on_any_event)
