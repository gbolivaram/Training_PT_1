"""
CompleteTaskCommand — el actor completó una tarea o tomó una decisión.

Flujo:
  1. Valida estado del proceso y nodo actual
  2. Guarda inputs en process_instances
  3. Marca node_state como COMPLETED
  4. Marca notificaciones del nodo como COMPLETADA
  5. Resuelve siguiente nodo (TransitionResolver)
  6. Si END → cierra proceso (ProcessFinalized)
  7. Si nodo normal → avanza (ProcessAdvanced → NotificationHandler lo capta)
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from core.commands.base import Command, CommandError
from core.events.bus import EventBus
from core.events.types import TaskCompleted, DecisionMade, ProcessAdvanced, ProcessFinalized
from core.state_machine.process_states import ProcessStateMachine
from core.state_machine.transitions import TransitionResolver
from repositories.process_repository import ProcessRepository
from repositories.node_state_repository import NodeStateRepository
from repositories.notification_repository import NotificationRepository


class CompleteTaskCommand(Command):

    def __init__(self, instance_id: str, node_id: str,
                 inputs: dict | None = None, decision: int | None = None):
        self.instance_id = instance_id
        self.node_id = node_id
        self.inputs = inputs or {}
        self.decision = decision

    def validate(self):
        inst = ProcessRepository.get(self.instance_id)
        if not inst:
            raise CommandError("Instancia no encontrada.")
        if not ProcessStateMachine.is_active(inst["estado"]):
            raise CommandError(f"Proceso en estado '{inst['estado']}', no acepta transiciones.")
        if inst["current_node"] != self.node_id:
            raise CommandError(f"Nodo activo es '{inst['current_node']}', no '{self.node_id}'.")

    def execute(self) -> dict:
        self.validate()

        from core.engine import load_procedure
        inst = ProcessRepository.get(self.instance_id)
        nodos = load_procedure(inst["pro_id"])
        node = nodos.get(self.node_id)
        if not node:
            raise CommandError(f"Nodo '{self.node_id}' no existe en el procedimiento.")

        bus = EventBus()

        # 1. Guardar inputs
        all_inputs = inst["inputs"]
        if self.inputs:
            all_inputs[self.node_id] = self.inputs

        # 2. Marcar node_state COMPLETED
        NodeStateRepository.update(self.instance_id, self.node_id, "COMPLETED")

        # 3. Marcar notificaciones como COMPLETADA
        for notif in NotificationRepository.for_instance(self.instance_id):
            if notif["node_id"] == self.node_id and notif["estado"] in ("PENDIENTE", "LEIDA"):
                NotificationRepository.mark(notif["id"], "COMPLETADA")

        # 4. Publicar evento de completado
        if self.decision is not None:
            label = TransitionResolver.decision_label(node, self.decision)
            bus.publish(DecisionMade(
                instance_id=self.instance_id,
                pro_id=inst["pro_id"],
                node_id=self.node_id,
                next_node_id="",
                decision=self.decision,
                decision_label=label,
                rol=node.get("rol", ""),
                payload={"titulo": node.get("titulo", self.node_id), "inputs": self.inputs},
            ))
        else:
            bus.publish(TaskCompleted(
                instance_id=self.instance_id,
                pro_id=inst["pro_id"],
                node_id=self.node_id,
                rol=node.get("rol", ""),
                payload={"titulo": node.get("titulo", self.node_id), "inputs": self.inputs},
            ))

        # 5. Resolver siguiente nodo
        try:
            next_id = TransitionResolver.next_node(node, self.decision)
        except ValueError as e:
            raise CommandError(str(e))

        if not next_id:
            raise CommandError("No se pudo resolver el siguiente nodo.")

        next_node = nodos.get(next_id)
        if not next_node:
            raise CommandError(f"Nodo siguiente '{next_id}' no existe.")

        # 6. Si es END → cerrar
        if TransitionResolver.is_end_node(next_node):
            estado_final = next_node.get("estado_final", "COMPLETADO")
            ProcessRepository.update(
                self.instance_id,
                current_node=next_id,
                estado=estado_final,
                inputs=all_inputs,
            )
            bus.publish(ProcessFinalized(
                instance_id=self.instance_id,
                pro_id=inst["pro_id"],
                end_node_id=next_id,
                estado_final=estado_final,
                payload={"titulo": next_node.get("titulo", next_id)},
            ))
            return {
                "status": "FINALIZADO",
                "node_id": next_id,
                "node": next_node,
                "instance_id": self.instance_id,
                "estado_final": estado_final,
            }

        # 7. Avanzar
        ProcessRepository.update(
            self.instance_id,
            current_node=next_id,
            inputs=all_inputs,
        )
        NodeStateRepository.create(self.instance_id, next_id, "IN_PROGRESS")

        # ProcessAdvanced → NotificationHandler lo capta y activa al siguiente actor
        bus.publish(ProcessAdvanced(
            instance_id=self.instance_id,
            pro_id=inst["pro_id"],
            next_node_id=next_id,
            next_node=next_node,
            payload={"titulo": next_node.get("titulo", next_id), "rol": next_node.get("rol", "")},
        ))

        return {
            "status": "AVANZADO",
            "node_id": next_id,
            "node": next_node,
            "instance_id": self.instance_id,
        }
