"""
BlockProcessCommand / UnblockProcessCommand — bloqueo/desbloqueo por impedimento externo.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from core.commands.base import Command, CommandError
from core.events.bus import EventBus
from core.events.types import ProcessBlocked, ProcessUnblocked
from core.state_machine.process_states import ProcessStateMachine
from repositories.process_repository import ProcessRepository
from repositories.node_state_repository import NodeStateRepository


class BlockProcessCommand(Command):

    def __init__(self, instance_id: str, node_id: str, motivo: str):
        self.instance_id = instance_id
        self.node_id = node_id
        self.motivo = motivo

    def validate(self):
        inst = ProcessRepository.get(self.instance_id)
        if not inst:
            raise CommandError("Instancia no encontrada.")
        if not ProcessStateMachine.is_active(inst["estado"]):
            raise CommandError(f"Proceso en estado '{inst['estado']}'.")

    def execute(self) -> dict:
        self.validate()
        inst = ProcessRepository.get(self.instance_id)

        NodeStateRepository.update(self.instance_id, self.node_id, "BLOCKED")
        ProcessRepository.update(self.instance_id, estado="BLOQUEADO")

        bus = EventBus()
        bus.publish(ProcessBlocked(
            instance_id=self.instance_id,
            pro_id=inst["pro_id"],
            node_id=self.node_id,
            motivo=self.motivo,
            payload={"titulo": f"[BLOQUEO] {self.node_id}",
                     "inputs": {"motivo_bloqueo": self.motivo}},
        ))
        return {"status": "BLOQUEADO", "instance_id": self.instance_id, "motivo": self.motivo}


class UnblockProcessCommand(Command):

    def __init__(self, instance_id: str):
        self.instance_id = instance_id

    def validate(self):
        inst = ProcessRepository.get(self.instance_id)
        if not inst:
            raise CommandError("Instancia no encontrada.")
        if inst["estado"] != "BLOQUEADO":
            raise CommandError(f"Proceso no está bloqueado (estado: '{inst['estado']}').")

    def execute(self) -> dict:
        self.validate()

        from core.engine import load_procedure
        inst = ProcessRepository.get(self.instance_id)
        nodos = load_procedure(inst["pro_id"])
        node = nodos.get(inst["current_node"], {})

        ProcessRepository.update(self.instance_id, estado="EN_CURSO")

        bus = EventBus()
        bus.publish(ProcessUnblocked(
            instance_id=self.instance_id,
            pro_id=inst["pro_id"],
            current_node=inst["current_node"],
            payload={"titulo": f"Proceso desbloqueado", "node": node,
                     "rol": node.get("rol", "")},
        ))
        return {"status": "REACTIVADO", "instance_id": self.instance_id,
                "current_node": inst["current_node"]}
