"""
API Flask — capa delgada sobre el CORE del Orquestador.

Esta capa solo:
  - Parsea y valida la entrada HTTP
  - Delega al componente CORE correspondiente
  - Serializa la respuesta

Nunca implementa lógica de flujo directamente.
"""
import json
import os
import sys
sys.path.insert(0, os.path.dirname(__file__))

from flask import Flask, jsonify, request, render_template
from models import (
    init_db, get_instance, list_instances,
    get_notifications_for_email, get_all_pending_notifications,
    get_notification, mark_notification, get_history_log, get_node_states,
)
from core.instance_manager import create_process, get_process, list_active
from core.state_engine import execute_transition, stop_process, block_process, unblock_process, load_procedure
from config import PROCEDURES, ROLE_CONTACTS

app = Flask(__name__)
init_db()


# ── Vistas HTML ──────────────────────────────────────────────────────────────

@app.route("/")
def dashboard():
    instances = list_instances()
    pending = get_all_pending_notifications()
    return render_template("dashboard.html",
        instances=instances,
        pending_count=len(pending),
        procedures=PROCEDURES,
        contacts=ROLE_CONTACTS,
    )


@app.route("/inbox/<email>")
def inbox(email):
    notifications = get_notifications_for_email(email)
    contact_name = next(
        (c["nombre"] for c in ROLE_CONTACTS.values() if c["email"] == email),
        email,
    )
    return render_template("inbox.html",
        notifications=notifications,
        email=email,
        contact_name=contact_name,
    )


@app.route("/task/<instance_id>/<node_id>")
def task_page(instance_id, node_id):
    inst = get_instance(instance_id)
    if not inst:
        return "Instancia no encontrada", 404
    nodos = load_procedure(inst["pro_id"])
    node = nodos.get(node_id)
    if not node:
        return "Tarea no encontrada", 404
    return render_template("task.html",
        instance=inst,
        node_id=node_id,
        node=node,
        is_current=(inst["current_node"] == node_id),
        is_active=(inst["estado"] == "EN_CURSO"),
        pro_info=PROCEDURES.get(inst["pro_id"], {}),
        history=get_history_log(instance_id),
        saved_inputs=inst["inputs"].get(node_id, {}),
    )


@app.route("/process/<instance_id>")
def process_detail(instance_id):
    inst = get_instance(instance_id)
    if not inst:
        return "Instancia no encontrada", 404
    nodos = load_procedure(inst["pro_id"])
    return render_template("process.html",
        instance=inst,
        nodos=nodos,
        pro_info=PROCEDURES.get(inst["pro_id"], {}),
        current_node=nodos.get(inst["current_node"], {}),
        history=get_history_log(instance_id),
        node_states=get_node_states(instance_id),
    )


# ── API: Ciclo de vida ───────────────────────────────────────────────────────

@app.route("/api/trigger", methods=["POST"])
def api_trigger():
    """Inicia una nueva instancia de procedimiento."""
    data = request.get_json(silent=True) or {}
    pro_id = data.get("pro_id", "PRO115")
    trigger_event = data.get("trigger_event", "Trigger manual")

    if pro_id not in PROCEDURES:
        return jsonify({"error": f"Procedimiento '{pro_id}' no configurado"}), 400

    try:
        instance_id = create_process(pro_id, trigger_event)

        # InstanceManager creó la instancia; NotificationDispatcher activa el primer actor
        from core.notification_dispatcher import dispatch_to_actor
        nodos = load_procedure(pro_id)
        primer_nodo = PROCEDURES[pro_id]["primer_nodo"]
        dispatch_to_actor(instance_id, pro_id, primer_nodo, nodos[primer_nodo])

        return jsonify({"ok": True, "instance_id": instance_id, "pro_id": pro_id})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/complete", methods=["POST"])
def api_complete():
    """Ejecuta una transición de estado (StateEngine)."""
    data = request.get_json(silent=True) or {}
    instance_id = data.get("instance_id")
    node_id = data.get("node_id")
    inputs = data.get("inputs") or {}
    decision = data.get("decision")

    if not instance_id or not node_id:
        return jsonify({"error": "Faltan instance_id o node_id"}), 400

    result = execute_transition(instance_id, node_id, inputs=inputs, decision=decision)
    if "error" in result:
        return jsonify(result), 400
    return jsonify(result)


@app.route("/api/stop", methods=["POST"])
def api_stop():
    """Detiene el proceso por condición crítica (StateEngine)."""
    data = request.get_json(silent=True) or {}
    instance_id = data.get("instance_id")
    node_id = data.get("node_id")
    motivo = (data.get("motivo") or "").strip()
    reported_by = data.get("reported_by", "")

    if not instance_id or not node_id or not motivo:
        return jsonify({"error": "Faltan instance_id, node_id o motivo"}), 400

    result = stop_process(instance_id, node_id, motivo, reported_by)
    if "error" in result:
        return jsonify(result), 400
    return jsonify(result)


@app.route("/api/block", methods=["POST"])
def api_block():
    """Bloquea el proceso por impedimento externo (StateEngine)."""
    data = request.get_json(silent=True) or {}
    instance_id = data.get("instance_id")
    node_id = data.get("node_id")
    motivo = (data.get("motivo") or "").strip()

    if not instance_id or not node_id or not motivo:
        return jsonify({"error": "Faltan instance_id, node_id o motivo"}), 400

    result = block_process(instance_id, node_id, motivo)
    if "error" in result:
        return jsonify(result), 400
    return jsonify(result)


@app.route("/api/unblock", methods=["POST"])
def api_unblock():
    """Reactiva un proceso bloqueado (StateEngine)."""
    data = request.get_json(silent=True) or {}
    instance_id = data.get("instance_id")
    if not instance_id:
        return jsonify({"error": "Falta instance_id"}), 400
    result = unblock_process(instance_id)
    if "error" in result:
        return jsonify(result), 400
    return jsonify(result)


# ── API: Consultas ───────────────────────────────────────────────────────────

@app.route("/api/instances")
def api_instances():
    return jsonify(list_instances())


@app.route("/api/instance/<instance_id>")
def api_instance(instance_id):
    inst = get_instance(instance_id)
    if not inst:
        return jsonify({"error": "not found"}), 404
    inst["history"] = get_history_log(instance_id)
    inst["node_states"] = get_node_states(instance_id)
    return jsonify(inst)


@app.route("/api/pending")
def api_pending():
    return jsonify(get_all_pending_notifications())


@app.route("/api/notification/<nid>/read", methods=["POST"])
def api_mark_read(nid):
    mark_notification(nid, "LEIDA", timestamp_field="read_at")
    return jsonify({"ok": True})


if __name__ == "__main__":
    app.run(debug=True, port=5001)
