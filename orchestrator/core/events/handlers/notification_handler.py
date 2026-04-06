"""
NotificationHandler — Observer que reacciona a eventos para activar actores.

Se suscribe a:
  - process.advanced   → despacha notificación al siguiente actor
  - process.stopped    → alerta de STOP a todos los roles
  - process.unblocked  → re-notifica al actor del nodo actual
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from core.events.types import ProcessAdvanced, ProcessStopped, ProcessUnblocked
from core.notifications.dispatcher import NotificationDispatcher


def on_process_advanced(event: ProcessAdvanced):
    """El proceso avanzó: activar al actor del nuevo nodo."""
    NotificationDispatcher.dispatch_task(
        instance_id=event.instance_id,
        pro_id=event.pro_id,
        node_id=event.next_node_id,
        node=event.next_node,
    )


def on_process_stopped(event: ProcessStopped):
    """STOP activado: alertar a todos los roles."""
    NotificationDispatcher.dispatch_stop(
        instance_id=event.instance_id,
        pro_id=event.pro_id,
        node_id=event.node_id,
        motivo=event.motivo,
        reported_by=event.reported_by,
    )


def on_process_unblocked(event: ProcessUnblocked):
    """Proceso desbloqueado: re-activar actor del nodo actual."""
    # El engine ya tiene el nodo en event.payload
    node = event.payload.get("node", {})
    if node:
        NotificationDispatcher.dispatch_task(
            instance_id=event.instance_id,
            pro_id=event.pro_id,
            node_id=event.current_node,
            node=node,
        )


def register(bus):
    """Registra todos los handlers de notificación en el EventBus."""
    bus.subscribe("process.advanced", on_process_advanced)
    bus.subscribe("process.stopped", on_process_stopped)
    bus.subscribe("process.unblocked", on_process_unblocked)
