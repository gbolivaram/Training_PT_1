"""
Máquina de estados a nivel de NODO.
Cada nodo de una instancia pasa por estos estados.
"""


class NodeStates:
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    STOPPED = "STOPPED"
    BLOCKED = "BLOCKED"

    TERMINAL = {COMPLETED, STOPPED}


VALID_NODE_TRANSITIONS = {
    NodeStates.PENDING: {NodeStates.IN_PROGRESS},
    NodeStates.IN_PROGRESS: {
        NodeStates.COMPLETED,
        NodeStates.STOPPED,
        NodeStates.BLOCKED,
    },
    NodeStates.BLOCKED: {NodeStates.IN_PROGRESS},
}


class NodeStateMachine:
    """Valida transiciones de estado a nivel de nodo."""

    @staticmethod
    def can_transition(current: str, target: str) -> bool:
        return target in VALID_NODE_TRANSITIONS.get(current, set())
