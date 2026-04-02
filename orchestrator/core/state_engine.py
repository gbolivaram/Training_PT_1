"""
StateEngine — núcleo de la máquina de estados.

Responsabilidades:
  - Validar que una transición es legal
  - Ejecutar la transición: guardar inputs, avanzar nodo, registrar en history_log
  - Controlar flujo: STOP y BLOQUEO
  - Delegar a TransitionLogic (siguiente nodo) y NotificationDispatcher (activar actor)

Este componente es el controlador central. La API solo lo llama —
nunca implementa lógica de flujo directamente.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import json
from config import PROCEDURES
from core.transition_logic import resolve_next, get_decision_label, is_stop_allowed
from core.notification_dispatcher import dispatch_to_actor, dispatch_stop_alert
import models

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")


def load_procedure(pro_id: str) -> dict:
    proc = PROCEDURES.get(pro_id)
    if not proc:
        raise ValueError(f"Procedimiento '{pro_id}' no registrado.")
    path = os.path.join(DATA_DIR, proc["data_file"])
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def execute_transition(
    instance_id: str,
    node_id: str,
    inputs: dict | None = None,
    decision: int | None = None,
) -> dict:
    """
    Ejecuta una transición de estado.

    Flujo:
      1. Validar instancia y nodo actual
      2. Guardar inputs del nodo completado
      3. Registrar en history_log con timestamp
      4. Marcar node_state del nodo actual como COMPLETED
      5. Resolver siguiente nodo (TransitionLogic)
      6. Si es END → cerrar proceso
      7. Si es nodo normal → update_instance + node_state nuevo + dispatch notificación
    """
    # ── 1. Validar ───────────────────────────────────────────────
    inst = models.get_instance(instance_id)
    if not inst:
        return {"error": "Instancia no encontrada."}
    if inst["estado"] != "EN_CURSO":
        return {"error": f"El proceso está en estado '{inst['estado']}' y no acepta transiciones."}
    if inst["current_node"] != node_id:
        return {"error": f"El nodo activo es '{inst['current_node']}', no '{node_id}'."}

    nodos = load_procedure(inst["pro_id"])
    node = nodos.get(node_id)
    if not node:
        return {"error": f"Nodo '{node_id}' no existe en el procedimiento."}

    # ── 2. Guardar inputs ────────────────────────────────────────
    all_inputs = inst["inputs"]
    if inputs:
        all_inputs[node_id] = inputs

    # ── 3. Registrar en history_log ───────────────────────────────
    decision_label = None
    if decision is not None:
        decision_label = get_decision_label(node, decision)

    models.append_history_log(
        instance_id=instance_id,
        node_id=node_id,
        titulo=node.get("titulo", node_id),
        rol=node.get("rol", ""),
        inputs=inputs or {},
        decision=decision,
        decision_label=decision_label,
    )

    # ── 4. Marcar nodo actual como COMPLETED ──────────────────────
    models.update_node_state(instance_id, node_id, "COMPLETED")

    # Marcar notificaciones de este nodo como actuadas
    for notif in models.get_notifications_for_instance(instance_id):
        if notif["node_id"] == node_id and notif["estado"] in ("PENDIENTE", "LEIDA"):
            models.mark_notification(notif["id"], "COMPLETADA")

    # ── 5. Resolver siguiente nodo ────────────────────────────────
    try:
        next_node_id = resolve_next(node, decision)
    except ValueError as e:
        return {"error": str(e)}

    if not next_node_id:
        return {"error": "No se pudo determinar el siguiente nodo."}

    next_node = nodos.get(next_node_id)
    if not next_node:
        return {"error": f"Nodo siguiente '{next_node_id}' no existe en el procedimiento."}

    # ── 6. Si es nodo END → cerrar proceso ────────────────────────
    if next_node.get("type") == "end":
        estado_final = next_node.get("estado_final", "COMPLETADO")
        models.update_instance(
            instance_id,
            current_node=next_node_id,
            estado=estado_final,
            inputs=all_inputs,
        )
        return {
            "status": "FINALIZADO",
            "node_id": next_node_id,
            "node": next_node,
            "instance_id": instance_id,
            "estado_final": estado_final,
        }

    # ── 7. Avanzar al siguiente nodo + activar siguiente actor ────
    models.update_instance(
        instance_id,
        current_node=next_node_id,
        inputs=all_inputs,
    )
    models.create_node_state(instance_id, next_node_id, "IN_PROGRESS")

    # NotificationDispatcher activa al siguiente actor
    dispatch_to_actor(
        instance_id=instance_id,
        pro_id=inst["pro_id"],
        node_id=next_node_id,
        node=next_node,
    )

    return {
        "status": "AVANZADO",
        "node_id": next_node_id,
        "node": next_node,
        "instance_id": instance_id,
    }


def stop_process(
    instance_id: str,
    node_id: str,
    motivo: str,
    reported_by: str = "",
) -> dict:
    """
    Detiene el proceso por condición crítica.
    Solo aplicable en nodos con allow_stop=true.
    """
    inst = models.get_instance(instance_id)
    if not inst:
        return {"error": "Instancia no encontrada."}
    if inst["estado"] != "EN_CURSO":
        return {"error": f"El proceso ya está en estado '{inst['estado']}'."}

    nodos = load_procedure(inst["pro_id"])
    node = nodos.get(node_id)
    if not node:
        return {"error": f"Nodo '{node_id}' no existe."}
    if not is_stop_allowed(node):
        return {"error": f"El nodo '{node_id}' no permite STOP."}

    # Registrar en history_log
    models.append_history_log(
        instance_id=instance_id,
        node_id=node_id,
        titulo=f"[STOP] {node.get('titulo', node_id)}",
        rol=node.get("rol", ""),
        inputs={"motivo_stop": motivo},
        decision=None,
        decision_label="STOP activado",
    )

    # Marcar nodo como STOPPED
    models.update_node_state(instance_id, node_id, "STOPPED")

    # Cerrar instancia
    models.update_instance(
        instance_id,
        current_node="END_STOP",
        estado="DETENIDO — REQUIERE INTERVENCIÓN",
    )

    # Alertar a todos los actores
    dispatch_stop_alert(
        instance_id=instance_id,
        pro_id=inst["pro_id"],
        node_id=node_id,
        motivo=motivo,
        reported_by=reported_by,
    )

    end_node = nodos.get("END_STOP", {})
    return {
        "status": "DETENIDO",
        "node_id": "END_STOP",
        "node": end_node,
        "instance_id": instance_id,
        "motivo": motivo,
    }


def block_process(
    instance_id: str,
    node_id: str,
    motivo: str,
    reported_by: str = "",
) -> dict:
    """
    Bloquea el proceso por impedimento externo (SIGO caído, sin contacto, etc).
    El proceso queda en BLOQUEADO hasta que se resuelva el impedimento.
    """
    inst = models.get_instance(instance_id)
    if not inst:
        return {"error": "Instancia no encontrada."}
    if inst["estado"] != "EN_CURSO":
        return {"error": f"El proceso ya está en estado '{inst['estado']}'."}

    models.append_history_log(
        instance_id=instance_id,
        node_id=node_id,
        titulo=f"[BLOQUEO] {node_id}",
        rol="",
        inputs={"motivo_bloqueo": motivo},
        decision=None,
        decision_label="BLOQUEO registrado",
    )
    models.update_node_state(instance_id, node_id, "BLOCKED")
    models.update_instance(instance_id, estado="BLOQUEADO")

    return {
        "status": "BLOQUEADO",
        "instance_id": instance_id,
        "node_id": node_id,
        "motivo": motivo,
    }


def unblock_process(instance_id: str) -> dict:
    """Reactiva un proceso bloqueado."""
    inst = models.get_instance(instance_id)
    if not inst:
        return {"error": "Instancia no encontrada."}
    if inst["estado"] != "BLOQUEADO":
        return {"error": f"El proceso no está bloqueado (estado: '{inst['estado']}')."}

    models.update_instance(instance_id, estado="EN_CURSO")

    # Re-activar el nodo actual
    nodos = load_procedure(inst["pro_id"])
    node = nodos.get(inst["current_node"], {})
    dispatch_to_actor(
        instance_id=instance_id,
        pro_id=inst["pro_id"],
        node_id=inst["current_node"],
        node=node,
    )
    return {"status": "REACTIVADO", "instance_id": instance_id, "current_node": inst["current_node"]}
