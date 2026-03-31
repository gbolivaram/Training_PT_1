"""
Motor del Orquestador de Ejecución Operacional.
Lee el JSON del procedimiento, avanza la máquina de estados,
y genera notificaciones al rol correcto en cada transición.
"""
import json
import os
from config import PROCEDURES, resolve_contacts
from models import (
    create_instance, get_instance, update_instance,
    create_notification, mark_notification, get_notifications_for_instance,
)

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")


def load_procedure(pro_id):
    """Carga el JSON de un procedimiento."""
    proc = PROCEDURES.get(pro_id)
    if not proc:
        raise ValueError(f"Procedimiento {pro_id} no encontrado")
    path = os.path.join(DATA_DIR, proc["data_file"])
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def trigger_process(pro_id, trigger_event="Manual"):
    """
    Gatilla un nuevo proceso: crea la instancia y notifica al primer rol.
    Retorna el instance_id.
    """
    proc = PROCEDURES[pro_id]
    nodos = load_procedure(pro_id)
    primer_nodo = proc["primer_nodo"]

    # Crear instancia
    instance_id = create_instance(pro_id, primer_nodo, trigger_event)

    # Notificar al primer rol
    _notify_node(instance_id, pro_id, primer_nodo, nodos)

    return instance_id


def get_current_task(instance_id):
    """
    Retorna el nodo actual de la instancia con toda su metadata.
    """
    inst = get_instance(instance_id)
    if not inst:
        return None
    nodos = load_procedure(inst["pro_id"])
    node_id = inst["current_node"]
    node = nodos.get(node_id)
    if not node:
        return None
    return {
        "instance": inst,
        "node_id": node_id,
        "node": node,
    }


def complete_task(instance_id, node_id, inputs=None, decision=None):
    """
    Marca una tarea como completada y avanza al siguiente nodo.
    - inputs: dict con los datos ingresados por el usuario
    - decision: para nodos tipo 'decision', el índice de la opción elegida
    Retorna el nuevo estado.
    """
    inst = get_instance(instance_id)
    if not inst:
        return {"error": "Instancia no encontrada"}
    if inst["estado"] != "EN_CURSO":
        return {"error": f"Proceso ya está en estado: {inst['estado']}"}
    if inst["current_node"] != node_id:
        return {"error": f"Nodo actual es {inst['current_node']}, no {node_id}"}

    nodos = load_procedure(inst["pro_id"])
    node = nodos.get(node_id)
    if not node:
        return {"error": f"Nodo {node_id} no existe en el procedimiento"}

    # Guardar inputs
    all_inputs = inst["inputs"]
    if inputs:
        all_inputs[node_id] = inputs

    # Agregar al historial
    history = inst["history"]
    history.append({
        "node_id": node_id,
        "titulo": node.get("titulo", ""),
        "inputs": inputs or {},
        "decision": decision,
    })

    # Marcar notificaciones de este nodo como actuadas
    for notif in get_notifications_for_instance(instance_id):
        if notif["node_id"] == node_id and notif["estado"] == "PENDIENTE":
            mark_notification(notif["id"], "COMPLETADA")

    # Determinar siguiente nodo
    next_node_id = _resolve_next(node, decision)
    if not next_node_id:
        return {"error": "No se pudo determinar el siguiente paso"}

    next_node = nodos.get(next_node_id)
    if not next_node:
        return {"error": f"Nodo siguiente {next_node_id} no existe"}

    # Si el siguiente es un nodo END, cerrar el proceso
    if next_node.get("type") == "end":
        update_instance(
            instance_id,
            current_node=next_node_id,
            estado=next_node.get("estado_final", "COMPLETADO"),
            inputs=all_inputs,
            history=history,
        )
        return {
            "status": "FINALIZADO",
            "node_id": next_node_id,
            "node": next_node,
            "instance_id": instance_id,
        }

    # Avanzar al siguiente nodo
    update_instance(
        instance_id,
        current_node=next_node_id,
        inputs=all_inputs,
        history=history,
    )

    # Notificar al rol del siguiente nodo
    _notify_node(instance_id, inst["pro_id"], next_node_id, nodos)

    return {
        "status": "AVANZADO",
        "node_id": next_node_id,
        "node": next_node,
        "instance_id": instance_id,
    }


def _resolve_next(node, decision=None):
    """Determina el siguiente nodo según el tipo."""
    node_type = node.get("type", "task")

    if node_type == "task":
        return node.get("next")

    if node_type == "decision":
        opciones = node.get("opciones", [])
        if decision is not None and 0 <= decision < len(opciones):
            return opciones[decision].get("next")
        return None

    return None


def _notify_node(instance_id, pro_id, node_id, nodos):
    """Crea notificaciones para todos los contactos del rol de un nodo."""
    node = nodos.get(node_id)
    if not node:
        return

    rol = node.get("rol", "")
    contacts = resolve_contacts(rol)
    pro_nombre = PROCEDURES[pro_id]["nombre"]

    for contact in contacts:
        link = f"/task/{instance_id}/{node_id}"
        titulo_notif = f"[{pro_id}] {node.get('titulo', node_id)}"
        mensaje = (
            f"Se requiere su acción en el procedimiento {pro_id} - {pro_nombre}.\n\n"
            f"Tarea: {node.get('titulo', '')}\n"
            f"Descripción: {node.get('descripcion', '')}\n\n"
            f"Haga click en el enlace para ejecutar esta tarea."
        )

        create_notification(
            instance_id=instance_id,
            node_id=node_id,
            rol=rol,
            titulo=titulo_notif,
            mensaje=mensaje,
            contact_name=contact["nombre"],
            contact_email=contact["email"],
            link=link,
        )
