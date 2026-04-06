"""
TriggerProcessCommand — instancia un proceso nuevo a partir de un evento.

Flujo:
  1. Valida que el pro_id existe en config
  2. Crea instancia via ProcessRepository
  3. Crea node_state inicial (IN_PROGRESS)
  4. Publica ProcessTriggered + ProcessAdvanced al EventBus
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from core.commands.base import Command, CommandError
from core.events.bus import EventBus
from core.events.types import ProcessTriggered, ProcessAdvanced
from repositories.process_repository import ProcessRepository
from repositories.node_state_repository import NodeStateRepository
from config import PROCEDURES


class TriggerProcessCommand(Command):

    def __init__(self, pro_id: str, trigger_event: str = "Manual"):
        self.pro_id = pro_id
        self.trigger_event = trigger_event
        self._nodos = None

    def validate(self):
        if self.pro_id not in PROCEDURES:
            raise CommandError(f"Procedimiento '{self.pro_id}' no está configurado.")

    def execute(self) -> dict:
        self.validate()

        proc = PROCEDURES[self.pro_id]
        primer_nodo = proc["primer_nodo"]

        # Cargar nodos del procedimiento
        from core.engine import load_procedure
        nodos = load_procedure(self.pro_id)

        # 1. Crear instancia
        instance_id = ProcessRepository.create(
            pro_id=self.pro_id,
            primer_nodo=primer_nodo,
            trigger_event=self.trigger_event,
        )

        # 2. Crear node_state inicial
        NodeStateRepository.create(instance_id, primer_nodo, "IN_PROGRESS")

        bus = EventBus()

        # 3. Publicar evento de trigger
        bus.publish(ProcessTriggered(
            instance_id=instance_id,
            pro_id=self.pro_id,
            payload={"trigger_event": self.trigger_event, "titulo": f"Proceso {self.pro_id} iniciado"},
        ))

        # 4. Publicar evento de avance (activa al primer actor via NotificationHandler)
        node = nodos.get(primer_nodo, {})
        bus.publish(ProcessAdvanced(
            instance_id=instance_id,
            pro_id=self.pro_id,
            next_node_id=primer_nodo,
            next_node=node,
            payload={"titulo": node.get("titulo", primer_nodo), "rol": node.get("rol", "")},
        ))

        return {
            "ok": True,
            "instance_id": instance_id,
            "pro_id": self.pro_id,
            "current_node": primer_nodo,
        }
