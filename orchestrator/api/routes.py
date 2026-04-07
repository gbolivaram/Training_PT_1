"""
API Routes — capa delgada que parsea HTTP y delega al Orchestrator.
Nunca implementa lógica de flujo. Solo:
  1. Parsea la request
  2. Llama a Orchestrator.metodo()
  3. Retorna el resultado como JSON/HTML
"""
from flask import Blueprint, jsonify, request, render_template
from core.engine import Orchestrator, load_procedure
from repositories.process_repository import ProcessRepository
from repositories.notification_repository import NotificationRepository
from repositories.history_repository import HistoryRepository
from repositories.node_state_repository import NodeStateRepository
import datetime
from config import PROCEDURES, ROLE_CONTACTS

api = Blueprint("api", __name__)
views = Blueprint("views", __name__)


# ── Vistas HTML ──────────────────────────────────────────────────────────────

@views.route("/")
def dashboard():
    instances = ProcessRepository.list_all()
    pending = NotificationRepository.all_pending()
    return render_template("dashboard.html",
        instances=instances,
        pending_count=len(pending),
        procedures=PROCEDURES,
        contacts=ROLE_CONTACTS,
    )


@views.route("/inbox/<email>")
def inbox(email):
    notifications = NotificationRepository.for_email(email)
    contact_name = next(
        (c["nombre"] for c in ROLE_CONTACTS.values() if c["email"] == email), email
    )
    return render_template("inbox.html",
        notifications=notifications, email=email, contact_name=contact_name,
    )


@views.route("/task/<instance_id>/<node_id>")
def task_page(instance_id, node_id):
    inst = ProcessRepository.get(instance_id)
    if not inst:
        return "Instancia no encontrada", 404
    nodos = load_procedure(inst["pro_id"])
    node = nodos.get(node_id)
    if not node:
        return "Tarea no encontrada", 404

    # Deadline info
    deadline_info = None
    node_states = NodeStateRepository.list_for_instance(instance_id)
    for ns in reversed(node_states):
        if ns["node_id"] == node_id and ns.get("deadline_at"):
            dl = ns["deadline_at"]
            now = datetime.datetime.now()
            dl_dt = datetime.datetime.fromisoformat(dl)
            mins = round((dl_dt - now).total_seconds() / 60, 1)
            deadline_info = {
                "deadline_at": dl,
                "minutes_remaining": mins,
                "is_overdue": mins < 0,
            }
            break

    return render_template("task.html",
        instance=inst, node_id=node_id, node=node,
        is_current=(inst["current_node"] == node_id),
        is_active=(inst["estado"] == "EN_CURSO"),
        pro_info=PROCEDURES.get(inst["pro_id"], {}),
        history=HistoryRepository.list_for_instance(instance_id),
        saved_inputs=inst["inputs"].get(node_id, {}),
        deadline=deadline_info,
    )


@views.route("/process/<instance_id>")
def process_detail(instance_id):
    inst = ProcessRepository.get(instance_id)
    if not inst:
        return "Instancia no encontrada", 404
    nodos = load_procedure(inst["pro_id"])
    return render_template("process.html",
        instance=inst, nodos=nodos,
        pro_info=PROCEDURES.get(inst["pro_id"], {}),
        current_node=nodos.get(inst["current_node"], {}),
        history=HistoryRepository.list_for_instance(instance_id),
        node_states=NodeStateRepository.list_for_instance(instance_id),
    )


# ── API: Commands ────────────────────────────────────────────────────────────

@api.route("/trigger", methods=["POST"])
def trigger():
    data = request.get_json(silent=True) or {}
    result = Orchestrator.trigger(
        pro_id=data.get("pro_id", "PRO115"),
        trigger_event=data.get("trigger_event", "Trigger manual"),
    )
    if "error" in result:
        return jsonify(result), 400
    return jsonify(result)


@api.route("/complete", methods=["POST"])
def complete():
    data = request.get_json(silent=True) or {}
    iid = data.get("instance_id")
    nid = data.get("node_id")
    if not iid or not nid:
        return jsonify({"error": "Faltan instance_id o node_id"}), 400
    result = Orchestrator.complete(iid, nid,
        inputs=data.get("inputs") or {},
        decision=data.get("decision"),
    )
    if "error" in result:
        return jsonify(result), 400
    return jsonify(result)


@api.route("/stop", methods=["POST"])
def stop():
    data = request.get_json(silent=True) or {}
    iid = data.get("instance_id")
    nid = data.get("node_id")
    motivo = (data.get("motivo") or "").strip()
    if not iid or not nid or not motivo:
        return jsonify({"error": "Faltan instance_id, node_id o motivo"}), 400
    result = Orchestrator.stop(iid, nid, motivo, data.get("reported_by", ""))
    if "error" in result:
        return jsonify(result), 400
    return jsonify(result)


@api.route("/block", methods=["POST"])
def block():
    data = request.get_json(silent=True) or {}
    iid = data.get("instance_id")
    nid = data.get("node_id")
    motivo = (data.get("motivo") or "").strip()
    if not iid or not nid or not motivo:
        return jsonify({"error": "Faltan campos"}), 400
    result = Orchestrator.block(iid, nid, motivo)
    if "error" in result:
        return jsonify(result), 400
    return jsonify(result)


@api.route("/unblock", methods=["POST"])
def unblock():
    data = request.get_json(silent=True) or {}
    iid = data.get("instance_id")
    if not iid:
        return jsonify({"error": "Falta instance_id"}), 400
    result = Orchestrator.unblock(iid)
    if "error" in result:
        return jsonify(result), 400
    return jsonify(result)


# ── API: Queries (no pasan por Orchestrator, van directo a Repository) ───────

@api.route("/instances")
def instances():
    return jsonify(ProcessRepository.list_all())


@api.route("/instance/<instance_id>")
def instance(instance_id):
    inst = ProcessRepository.get(instance_id)
    if not inst:
        return jsonify({"error": "not found"}), 404
    inst["history"] = HistoryRepository.list_for_instance(instance_id)
    inst["node_states"] = NodeStateRepository.list_for_instance(instance_id)
    return jsonify(inst)


@api.route("/pending")
def pending():
    return jsonify(NotificationRepository.all_pending())


@api.route("/notification/<nid>/read", methods=["POST"])
def mark_read(nid):
    NotificationRepository.mark(nid, "LEIDA", timestamp_field="read_at")
    return jsonify({"ok": True})


@api.route("/overdue")
def overdue():
    """Retorna nodos cuyo deadline ya venció."""
    return jsonify(NodeStateRepository.overdue())


@api.route("/deadlines")
def deadlines():
    """Retorna todos los nodos activos con deadline (vencidos y por vencer)."""
    import datetime
    now = datetime.datetime.now().isoformat(timespec="seconds")
    items = NodeStateRepository.active_with_deadline()
    for item in items:
        dl = item.get("deadline_at")
        if dl:
            item["is_overdue"] = dl < now
            # Minutos restantes (negativo = vencido)
            dl_dt = datetime.datetime.fromisoformat(dl)
            now_dt = datetime.datetime.now()
            item["minutes_remaining"] = round((dl_dt - now_dt).total_seconds() / 60, 1)
    return jsonify(items)
