"""
Tipos de eventos del sistema.
Cada evento tiene un nombre y un payload tipado.
El EventBus los publica; los handlers los consumen.
"""
from dataclasses import dataclass, field


@dataclass
class Event:
    """Base para todos los eventos."""
    instance_id: str = ""
    pro_id: str = ""
    name: str = ""
    payload: dict = field(default_factory=dict)


# ── Eventos de ciclo de vida ─────────────────────────────────

@dataclass
class ProcessTriggered(Event):
    """Un proceso fue instanciado por un evento externo."""
    name: str = "process.triggered"


@dataclass
class TaskCompleted(Event):
    """Un actor completó una tarea."""
    node_id: str = ""
    next_node_id: str = ""
    rol: str = ""
    name: str = "task.completed"


@dataclass
class DecisionMade(Event):
    """Un actor tomó una decisión en un nodo de decisión."""
    node_id: str = ""
    next_node_id: str = ""
    decision: int = 0
    decision_label: str = ""
    rol: str = ""
    name: str = "decision.made"


@dataclass
class ProcessAdvanced(Event):
    """El proceso avanzó a un nuevo nodo. Requiere activar al siguiente actor."""
    next_node_id: str = ""
    next_node: dict = field(default_factory=dict)
    name: str = "process.advanced"


@dataclass
class ProcessFinalized(Event):
    """El proceso llegó a un nodo END."""
    end_node_id: str = ""
    estado_final: str = ""
    name: str = "process.finalized"


@dataclass
class ProcessStopped(Event):
    """El proceso fue detenido por condición crítica."""
    node_id: str = ""
    motivo: str = ""
    reported_by: str = ""
    name: str = "process.stopped"


@dataclass
class ProcessBlocked(Event):
    """El proceso fue bloqueado por impedimento externo."""
    node_id: str = ""
    motivo: str = ""
    name: str = "process.blocked"


@dataclass
class ProcessUnblocked(Event):
    """El proceso fue reactivado después de un bloqueo."""
    current_node: str = ""
    name: str = "process.unblocked"
