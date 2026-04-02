"""
InstanceManager — gestiona el ciclo de vida de instancias de proceso.

Responsabilidades:
  - Crear una instancia nueva con su nodo inicial
  - Registrar el nodo inicial en node_state
  - Consultar el estado actual de una instancia
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import json
import models
from config import PROCEDURES


def create_process(pro_id: str, trigger_event: str = "") -> str:
    """
    Crea una instancia nueva del procedimiento y la deja lista para ejecución.
    Retorna el instance_id.
    """
    proc = PROCEDURES.get(pro_id)
    if not proc:
        raise ValueError(f"Procedimiento '{pro_id}' no está registrado en PROCEDURES.")

    primer_nodo = proc["primer_nodo"]

    # 1. Crear la instancia de proceso
    instance_id = models.create_instance(
        pro_id=pro_id,
        primer_nodo=primer_nodo,
        trigger_event=trigger_event,
    )

    # 2. Registrar el nodo inicial como IN_PROGRESS en node_state
    models.create_node_state(
        instance_id=instance_id,
        node_id=primer_nodo,
        estado="IN_PROGRESS",
    )

    return instance_id


def get_process(instance_id: str) -> dict | None:
    """Devuelve el estado completo de una instancia."""
    return models.get_instance(instance_id)


def list_active() -> list[dict]:
    """Lista todas las instancias EN_CURSO."""
    return [i for i in models.list_instances() if i["estado"] == "EN_CURSO"]
