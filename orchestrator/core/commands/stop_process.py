"""
StopProcessCommand — detiene el proceso por condición crítica.
Solo aplicable en nodos con allow_stop=true.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from core.commands.base import Command, CommandError
from core.events.bus import EventBus
from core.events.types import ProcessStopped
from core.state_machine.process_states import ProcessStateMachine
from core.state_machine.transitions import TransitionResolver
from repositories.process_repository import ProcessRepository
from repositories.node_state_repository import NodeStateRepository


class StopProcessCommand(Command):

    def __init__(self, instance_id: str, node_id: str, motivo: str, reported_by: str = ""):
        self.instance_id = instance_id
        self.node_id = node_id
        self.motivo = motivo
        self.reported_by = reported_by

    def validate(self):
        inst = ProcessRepository.get(self.instance_id)
        if not inst:
            raise CommandError("Instancia no encontrada.")
        if not ProcessStateMachine.is_active(inst["estado"]):
            raise CommandError(f"Proceso en estado '{inst['estado']}'.")

    def execute(self) -> dict:
        self.validate()

        from core.engine import load_procedure
        inst = ProcessRepository.get(self.instance_id)
        nodos = load_procedure(inst["pro_id"])
        node = nodos.get(self.node_id)

        if not node:
            raise CommandError(f"Nodo '{self.node_id}' no existe.")
        if not TransitionResolver.allows_stop(node):
            raise CommandError(f"Nodo '{self.node_id}' no permite STOP.")

        # Marcar nodo como STOPPED
        NodeStateRepository.update(self.instance_id, self.node_id, "STOPPED")

        # Cerrar proceso
        ProcessRepository.update(
            self.instance_id,
            current_node="END_STOP",
            estado="DETENIDO — REQUIERE INTERVENCIÓN",
        )

        # Publicar → NotificationHandler enviará alerta STOP a todos
        bus = EventBus()
        bus.publish(ProcessStopped(
            instance_id=self.instance_id,
            pro_id=inst["pro_id"],
            node_id=self.node_id,
            motivo=self.motivo,
            reported_by=self.reported_by,
            payload={"titulo": f"[STOP] {node.get('titulo', self.node_id)}",
                     "inputs": {"motivo_stop": self.motivo}},
        ))

        end_node = nodos.get("END_STOP", {})
        return {
            "status": "DETENIDO",
            "node_id": "END_STOP",
            "node": end_node,
            "instance_id": self.instance_id,
            "motivo": self.motivo,
        }
