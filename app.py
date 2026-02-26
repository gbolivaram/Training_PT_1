import json
import sqlite3
import uuid
import datetime
import os
from flask import Flask, jsonify, request, render_template, send_from_directory, g

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = "/tmp/database.db" if os.environ.get("VERCEL") else os.path.join(BASE_DIR, "database.db")
NODOS_PATH  = os.path.join(BASE_DIR, "nodos.json")
AREAS_PATH  = os.path.join(BASE_DIR, "areas.json")
PRO114_PATH = os.path.join(BASE_DIR, "pro114.json")
PRO115_PATH = os.path.join(BASE_DIR, "pro115.json")

# ── DB ────────────────────────────────────────────────────────────────────────

def get_db():
    if "db" not in g:
        init_db()
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db

@app.teardown_appcontext
def close_db(exc):
    db = g.pop("db", None)
    if db:
        db.close()

def init_db():
    db = sqlite3.connect(DB_PATH)
    db.executescript("""
        CREATE TABLE IF NOT EXISTS sessions (
            id          TEXT PRIMARY KEY,
            created_at  TEXT NOT NULL,
            updated_at  TEXT NOT NULL,
            estado      TEXT NOT NULL DEFAULT 'EN_CURSO',
            pro_id      TEXT NOT NULL DEFAULT 'PRO141',
            area_id     TEXT NOT NULL DEFAULT 'inventario',
            current_node TEXT NOT NULL DEFAULT 'S0_alcance',
            history     TEXT NOT NULL DEFAULT '[]',
            decisiones  TEXT NOT NULL DEFAULT '[]',
            bloqueos    TEXT NOT NULL DEFAULT '[]',
            inputs      TEXT NOT NULL DEFAULT '{}',
            logs        TEXT NOT NULL DEFAULT '[]'
        );
    """)
    db.commit()
    db.close()

# ── Helpers ───────────────────────────────────────────────────────────────────

def now_iso():
    return datetime.datetime.now().isoformat(timespec="seconds")

def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)

def load_nodos_for_pro(pro_id):
    areas = load_json(AREAS_PATH)
    pro = areas["pros"].get(pro_id)
    if not pro:
        return {}
    data_file = pro["data"]
    path = os.path.join(BASE_DIR, data_file)
    return load_json(path)

# ── Routes ────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/static/docs/<path:filename>")
def serve_docs(filename):
    return send_from_directory(os.path.join(BASE_DIR, "static", "docs"), filename)

# Legacy: keep /api/nodos for backward compat
@app.route("/api/nodos")
def api_nodos():
    return jsonify(load_json(NODOS_PATH))

@app.route("/api/areas")
def api_areas():
    return jsonify(load_json(AREAS_PATH))

@app.route("/api/pro/<pro_id>/nodos")
def api_pro_nodos(pro_id):
    try:
        return jsonify(load_nodos_for_pro(pro_id))
    except Exception as e:
        return jsonify({"error": str(e)}), 404

# ── AI chat endpoint ───────────────────────────────────────────────────────────

@app.route("/api/ai/chat", methods=["POST"])
def ai_chat():
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return jsonify({
            "reply": "El asistente IA estará disponible pronto. Por ahora, utiliza la opción 'Ejecutar tarea' para acceder a los procedimientos guiados.",
            "ready": False
        })

    data = request.get_json()
    messages = data.get("messages", [])
    pro_id   = data.get("pro_id", "")
    area_id  = data.get("area_id", "")

    try:
        import anthropic
        areas = load_json(AREAS_PATH)
        pro_info = areas["pros"].get(pro_id, {})
        pro_nombre = pro_info.get("nombre", pro_id)
        nodos = load_nodos_for_pro(pro_id) if pro_id else {}
        nodos_resumen = "\n".join([
            f"- {nid}: {n.get('titulo','')}" for nid, n in nodos.items()
        ]) if nodos else "(sin procedimiento seleccionado)"

        system_prompt = f"""Eres un asistente experto en procedimientos operativos de una empresa del sector eléctrico chileno.
El usuario trabaja en el área: {area_id or 'no especificada'}.
Procedimiento de referencia: {pro_nombre or 'no seleccionado'}.

Pasos del procedimiento:
{nodos_resumen}

Tu rol es:
- Responder preguntas sobre el procedimiento de forma clara y concisa.
- Ayudar a interpretar pasos, roles y validaciones.
- Orientar al usuario sobre qué paso ejecutar según su situación.
- NO tomar decisiones operativas críticas por el usuario.
- Si el usuario necesita ejecutar el procedimiento formalmente, recomendar usar la opción "Ejecutar tarea".

Responde siempre en español, de forma directa y útil."""

        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1024,
            system=system_prompt,
            messages=messages
        )
        reply = response.content[0].text
        return jsonify({"reply": reply, "ready": True})

    except Exception as e:
        return jsonify({"reply": f"Error al conectar con el asistente: {str(e)}", "ready": False}), 500

# ── Session management ────────────────────────────────────────────────────────

@app.route("/api/session", methods=["POST"])
def create_session():
    data = request.get_json(silent=True) or {}
    pro_id  = data.get("pro_id", "PRO141")
    area_id = data.get("area_id", "inventario")

    areas = load_json(AREAS_PATH)
    pro = areas["pros"].get(pro_id, {})
    first_node = pro.get("primer_nodo", "S0_alcance")

    sid = str(uuid.uuid4())
    ts  = now_iso()
    db  = get_db()
    db.execute(
        "INSERT INTO sessions (id, created_at, updated_at, estado, pro_id, area_id, current_node) VALUES (?,?,?,?,?,?,?)",
        (sid, ts, ts, "EN_CURSO", pro_id, area_id, first_node)
    )
    db.commit()
    return jsonify({
        "session_id":   sid,
        "pro_id":       pro_id,
        "area_id":      area_id,
        "current_node": first_node,
        "estado":       "EN_CURSO"
    })

@app.route("/api/session/<sid>")
def get_session(sid):
    db = get_db()
    row = db.execute("SELECT * FROM sessions WHERE id=?", (sid,)).fetchone()
    if not row:
        return jsonify({"error": "not found"}), 404
    return jsonify({
        "session_id":   sid,
        "pro_id":       row["pro_id"],
        "area_id":      row["area_id"],
        "estado":       row["estado"],
        "current_node": row["current_node"],
        "history":      json.loads(row["history"]),
        "decisiones":   json.loads(row["decisiones"]),
        "bloqueos":     json.loads(row["bloqueos"]),
        "inputs":       json.loads(row["inputs"]),
        "logs":         json.loads(row["logs"]),
        "created_at":   row["created_at"],
        "updated_at":   row["updated_at"]
    })

@app.route("/api/session/<sid>", methods=["PUT"])
def update_session(sid):
    data = request.get_json()
    db   = get_db()
    row  = db.execute("SELECT * FROM sessions WHERE id=?", (sid,)).fetchone()
    if not row:
        return jsonify({"error": "not found"}), 404

    ts = now_iso()
    db.execute("""
        UPDATE sessions SET
            updated_at=?, estado=?, current_node=?,
            history=?, decisiones=?, bloqueos=?, inputs=?, logs=?
        WHERE id=?
    """, (
        ts,
        data.get("estado",       row["estado"]),
        data.get("current_node", row["current_node"]),
        json.dumps(data.get("history",    json.loads(row["history"])),    ensure_ascii=False),
        json.dumps(data.get("decisiones", json.loads(row["decisiones"])), ensure_ascii=False),
        json.dumps(data.get("bloqueos",   json.loads(row["bloqueos"])),   ensure_ascii=False),
        json.dumps(data.get("inputs",     json.loads(row["inputs"])),     ensure_ascii=False),
        json.dumps(data.get("logs",       json.loads(row["logs"])),       ensure_ascii=False),
        sid
    ))
    db.commit()
    return jsonify({"ok": True, "updated_at": ts})

@app.route("/api/session/<sid>/export")
def export_session(sid):
    db = get_db()
    row = db.execute("SELECT * FROM sessions WHERE id=?", (sid,)).fetchone()
    if not row:
        return jsonify({"error": "not found"}), 404

    pro_id = row["pro_id"]
    areas  = load_json(AREAS_PATH)
    pro    = areas["pros"].get(pro_id, {})

    payload = {
        "proceso":      f'{pro_id} – {pro.get("nombre", pro_id)}',
        "session_id":   sid,
        "pro_id":       pro_id,
        "area_id":      row["area_id"],
        "estado":       row["estado"],
        "current_node": row["current_node"],
        "created_at":   row["created_at"],
        "updated_at":   row["updated_at"],
        "history":      json.loads(row["history"]),
        "decisiones":   json.loads(row["decisiones"]),
        "bloqueos":     json.loads(row["bloqueos"]),
        "inputs":       json.loads(row["inputs"]),
        "logs":         json.loads(row["logs"]),
        "export_ts":    now_iso()
    }
    resp = app.response_class(
        response=json.dumps(payload, ensure_ascii=False, indent=2),
        mimetype="application/json"
    )
    resp.headers["Content-Disposition"] = f"attachment; filename={pro_id}_{sid[:8]}.json"
    return resp

if __name__ == "__main__":
    init_db()
    app.run(debug=True, port=5000)
