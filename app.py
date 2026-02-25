import json
import sqlite3
import uuid
import datetime
import os
from flask import Flask, jsonify, request, render_template, send_from_directory, g

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Vercel only allows writes to /tmp; locally use project dir
DB_PATH = "/tmp/database.db" if os.environ.get("VERCEL") else os.path.join(BASE_DIR, "database.db")
NODOS_PATH = os.path.join(BASE_DIR, "nodos.json")

# ── DB ───────────────────────────────────────────────────────────────────────

def get_db():
    if "db" not in g:
        init_db()  # no-op if table already exists
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

# ── Helpers ──────────────────────────────────────────────────────────────────

def now_iso():
    return datetime.datetime.now().isoformat(timespec="seconds")

def load_nodos():
    with open(NODOS_PATH, encoding="utf-8") as f:
        return json.load(f)

# ── Routes ───────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/static/docs/<path:filename>")
def serve_docs(filename):
    return send_from_directory(os.path.join(BASE_DIR, "static", "docs"), filename)

@app.route("/api/nodos")
def api_nodos():
    return jsonify(load_nodos())

# Session management
@app.route("/api/session", methods=["POST"])
def create_session():
    sid = str(uuid.uuid4())
    ts = now_iso()
    db = get_db()
    db.execute(
        "INSERT INTO sessions (id, created_at, updated_at, estado, current_node) VALUES (?,?,?,?,?)",
        (sid, ts, ts, "EN_CURSO", "S0_alcance")
    )
    db.commit()
    return jsonify({"session_id": sid, "current_node": "S0_alcance", "estado": "EN_CURSO"})

@app.route("/api/session/<sid>")
def get_session(sid):
    db = get_db()
    row = db.execute("SELECT * FROM sessions WHERE id=?", (sid,)).fetchone()
    if not row:
        return jsonify({"error": "not found"}), 404
    return jsonify({
        "session_id": sid,
        "estado": row["estado"],
        "current_node": row["current_node"],
        "history": json.loads(row["history"]),
        "decisiones": json.loads(row["decisiones"]),
        "bloqueos": json.loads(row["bloqueos"]),
        "inputs": json.loads(row["inputs"]),
        "logs": json.loads(row["logs"]),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"]
    })

@app.route("/api/session/<sid>", methods=["PUT"])
def update_session(sid):
    data = request.get_json()
    db = get_db()
    row = db.execute("SELECT * FROM sessions WHERE id=?", (sid,)).fetchone()
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
        data.get("estado", row["estado"]),
        data.get("current_node", row["current_node"]),
        json.dumps(data.get("history", json.loads(row["history"])), ensure_ascii=False),
        json.dumps(data.get("decisiones", json.loads(row["decisiones"])), ensure_ascii=False),
        json.dumps(data.get("bloqueos", json.loads(row["bloqueos"])), ensure_ascii=False),
        json.dumps(data.get("inputs", json.loads(row["inputs"])), ensure_ascii=False),
        json.dumps(data.get("logs", json.loads(row["logs"])), ensure_ascii=False),
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
    payload = {
        "proceso": "PRO141 – Tratamiento de materiales obsoletos y análisis de obsolescencia",
        "session_id": sid,
        "estado": row["estado"],
        "current_node": row["current_node"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        "history": json.loads(row["history"]),
        "decisiones": json.loads(row["decisiones"]),
        "bloqueos": json.loads(row["bloqueos"]),
        "inputs": json.loads(row["inputs"]),
        "logs": json.loads(row["logs"]),
        "export_ts": now_iso()
    }
    resp = app.response_class(
        response=json.dumps(payload, ensure_ascii=False, indent=2),
        mimetype="application/json"
    )
    resp.headers["Content-Disposition"] = f"attachment; filename=PRO141_{sid[:8]}.json"
    return resp

if __name__ == "__main__":
    init_db()
    app.run(debug=True, port=5000)
