"""
Orquestador de Ejecución Operacional - Colbun S.A.
Aplicación web Flask con:
- Dashboard de procesos activos
- Bandeja de notificaciones por usuario (simulated inbox)
- HMI de ejecución de tareas
- Trigger manual de procedimientos
"""
import json
from flask import Flask, jsonify, request, render_template, redirect, url_for
from models import (
    init_db, get_instance, list_instances,
    get_notifications_for_email, get_all_pending_notifications,
    get_notification, mark_notification,
)
from engine import trigger_process, get_current_task, complete_task, load_procedure
from config import PROCEDURES, ROLE_CONTACTS

app = Flask(__name__)

# ── Inicializar DB ───────────────────────────────────────────────────────────
init_db()

# ── Páginas principales ─────────────────────────────────────────────────────

@app.route("/")
def index():
    """Dashboard principal: procesos activos y acceso rápido."""
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
    """Bandeja de notificaciones de un usuario específico."""
    notifications = get_notifications_for_email(email)
    contact_name = email
    for c in ROLE_CONTACTS.values():
        if c["email"] == email:
            contact_name = c["nombre"]
            break
    return render_template("inbox.html",
        notifications=notifications,
        email=email,
        contact_name=contact_name,
    )


@app.route("/task/<instance_id>/<node_id>")
def task_page(instance_id, node_id):
    """HMI de ejecución de una tarea específica."""
    inst = get_instance(instance_id)
    if not inst:
        return "Instancia no encontrada", 404

    nodos = load_procedure(inst["pro_id"])
    node = nodos.get(node_id)
    if not node:
        return "Tarea no encontrada", 404

    is_current = inst["current_node"] == node_id
    pro_info = PROCEDURES.get(inst["pro_id"], {})

    return render_template("task.html",
        instance=inst,
        node_id=node_id,
        node=node,
        is_current=is_current,
        pro_info=pro_info,
        history=inst["history"],
        saved_inputs=inst["inputs"].get(node_id, {}),
    )


@app.route("/process/<instance_id>")
def process_detail(instance_id):
    """Vista detallada de un proceso con su historial."""
    inst = get_instance(instance_id)
    if not inst:
        return "Instancia no encontrada", 404
    nodos = load_procedure(inst["pro_id"])
    pro_info = PROCEDURES.get(inst["pro_id"], {})
    current_node = nodos.get(inst["current_node"], {})
    return render_template("process.html",
        instance=inst,
        nodos=nodos,
        pro_info=pro_info,
        current_node=current_node,
    )


# ── API endpoints ───────────────────────────────────────────────────────────

@app.route("/api/trigger", methods=["POST"])
def api_trigger():
    """Trigger manual: inicia un nuevo procedimiento."""
    data = request.get_json(silent=True) or {}
    pro_id = data.get("pro_id", "PRO115")
    trigger_event = data.get("trigger_event", "Trigger manual desde dashboard")

    if pro_id not in PROCEDURES:
        return jsonify({"error": f"Procedimiento {pro_id} no configurado"}), 400

    instance_id = trigger_process(pro_id, trigger_event)
    return jsonify({"ok": True, "instance_id": instance_id, "pro_id": pro_id})


@app.route("/api/complete", methods=["POST"])
def api_complete():
    """Completa una tarea y avanza el proceso."""
    data = request.get_json(silent=True) or {}
    instance_id = data.get("instance_id")
    node_id = data.get("node_id")
    inputs = data.get("inputs", {})
    decision = data.get("decision")

    if not instance_id or not node_id:
        return jsonify({"error": "Faltan instance_id o node_id"}), 400

    result = complete_task(instance_id, node_id, inputs=inputs, decision=decision)

    if "error" in result:
        return jsonify(result), 400

    return jsonify(result)


@app.route("/api/notification/<nid>/read", methods=["POST"])
def api_mark_read(nid):
    """Marca una notificación como leída."""
    mark_notification(nid, "LEIDA", timestamp_field="read_at")
    return jsonify({"ok": True})


@app.route("/api/instances")
def api_instances():
    """Lista todas las instancias de procesos."""
    return jsonify(list_instances())


@app.route("/api/pending")
def api_pending():
    """Lista todas las notificaciones pendientes."""
    return jsonify(get_all_pending_notifications())


if __name__ == "__main__":
    app.run(debug=True, port=5001)
