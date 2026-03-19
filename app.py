import json
import sqlite3
import uuid
import datetime
import os
from flask import Flask, jsonify, request, render_template, send_from_directory, g

app = Flask(__name__)

BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
_raw_db_url  = os.environ.get("DATABASE_URL", "")
# Supabase / psycopg2 requiere postgresql://, no postgres://
DATABASE_URL = _raw_db_url.replace("postgres://", "postgresql://", 1) if _raw_db_url else None
USE_PG       = bool(DATABASE_URL)                      # True en Vercel, False local

# En Vercel el filesystem es read-only; /tmp sí es escribible
_sqlite_dir  = "/tmp" if os.path.exists("/tmp") and not os.access(BASE_DIR, os.W_OK) else BASE_DIR
DB_PATH      = os.path.join(_sqlite_dir, "database.db")   # Solo se usa en local
NODOS_PATH   = os.path.join(BASE_DIR, "nodos.json")
AREAS_PATH   = os.path.join(BASE_DIR, "areas.json")
MANUALES_PATH = os.path.join(BASE_DIR, "manuales.json")

# ── Esquema de tablas ─────────────────────────────────────────────────────────

TABLES = [
    """
    CREATE TABLE IF NOT EXISTS sessions (
        id           TEXT PRIMARY KEY,
        created_at   TEXT NOT NULL,
        updated_at   TEXT NOT NULL,
        estado       TEXT NOT NULL DEFAULT 'EN_CURSO',
        pro_id       TEXT NOT NULL DEFAULT 'PRO141',
        area_id      TEXT NOT NULL DEFAULT 'inventario',
        current_node TEXT NOT NULL DEFAULT 'S0_alcance',
        history      TEXT NOT NULL DEFAULT '[]',
        decisiones   TEXT NOT NULL DEFAULT '[]',
        bloqueos     TEXT NOT NULL DEFAULT '[]',
        inputs       TEXT NOT NULL DEFAULT '{}',
        logs         TEXT NOT NULL DEFAULT '[]'
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS feedback (
        id          TEXT PRIMARY KEY,
        created_at  TEXT NOT NULL,
        pantalla    TEXT NOT NULL,
        area_id     TEXT NOT NULL DEFAULT '',
        pro_id      TEXT NOT NULL DEFAULT '',
        comentario  TEXT NOT NULL
    )
    """
]

# ── DB — abstracción SQLite / PostgreSQL ──────────────────────────────────────

def init_db():
    """Crea las tablas si no existen (se llama una vez al iniciar)."""
    if USE_PG:
        import psycopg2
        conn = psycopg2.connect(DATABASE_URL)
        cur  = conn.cursor()
        for sql in TABLES:
            cur.execute(sql)
        conn.commit()
        cur.close()
        conn.close()
    else:
        conn = sqlite3.connect(DB_PATH)
        for sql in TABLES:
            conn.execute(sql)
        conn.commit()
        conn.close()


def get_db():
    """Devuelve la conexión activa para este request."""
    if "db" not in g:
        if USE_PG:
            import psycopg2, psycopg2.extras
            g.db = psycopg2.connect(
                DATABASE_URL,
                cursor_factory=psycopg2.extras.RealDictCursor
            )
        else:
            g.db = sqlite3.connect(DB_PATH)
            g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(exc):
    db = g.pop("db", None)
    if db:
        db.close()


def _sql(sql):
    """Adapta los placeholders ? → %s para PostgreSQL."""
    return sql.replace("?", "%s") if USE_PG else sql


def db_run(sql, params=()):
    """Ejecuta una instrucción sin retorno (INSERT / UPDATE)."""
    conn = get_db()
    if USE_PG:
        cur = conn.cursor()
        cur.execute(_sql(sql), params)
        conn.commit()
        cur.close()
    else:
        conn.execute(sql, params)
        conn.commit()


def db_one(sql, params=()):
    """Ejecuta y retorna una fila como dict (o None)."""
    conn = get_db()
    if USE_PG:
        cur = conn.cursor()
        cur.execute(_sql(sql), params)
        row = cur.fetchone()
        cur.close()
        return dict(row) if row else None
    else:
        row = conn.execute(sql, params).fetchone()
        return dict(row) if row else None


def db_all(sql, params=()):
    """Ejecuta y retorna todas las filas como lista de dicts."""
    conn = get_db()
    if USE_PG:
        cur = conn.cursor()
        cur.execute(_sql(sql), params)
        rows = cur.fetchall()
        cur.close()
        return [dict(r) for r in rows]
    else:
        rows = conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]

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
    return load_json(os.path.join(BASE_DIR, pro["data"]))

# ── Routes ────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/static/docs/<path:filename>")
def serve_docs(filename):
    return send_from_directory(os.path.join(BASE_DIR, "static", "docs"), filename)

@app.route("/api/nodos")
def api_nodos():
    return jsonify(load_json(NODOS_PATH))

@app.route("/api/areas")
def api_areas():
    return jsonify(load_json(AREAS_PATH))

@app.route("/api/manuales")
def api_manuales():
    return jsonify(load_json(MANUALES_PATH))

@app.route("/api/manuales/<area_id>")
def api_manuales_area(area_id):
    data = load_json(MANUALES_PATH)
    ids  = data["por_area"].get(area_id, [])
    return jsonify([data["manuales"][m] for m in ids if m in data["manuales"]])

@app.route("/api/pro/<pro_id>/nodos")
def api_pro_nodos(pro_id):
    try:
        return jsonify(load_nodos_for_pro(pro_id))
    except Exception as e:
        return jsonify({"error": str(e)}), 404

# ── AI chat ───────────────────────────────────────────────────────────────────

@app.route("/api/ai/chat", methods=["POST"])
def ai_chat():
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return jsonify({
            "reply": "El asistente IA estará disponible pronto. Por ahora, utiliza la opción 'Ejecutar tarea' para acceder a los procedimientos guiados.",
            "ready": False
        })

    data     = request.get_json()
    messages = data.get("messages", [])
    pro_id   = data.get("pro_id", "")
    area_id  = data.get("area_id", "")

    try:
        import anthropic
        areas      = load_json(AREAS_PATH)
        pro_info   = areas["pros"].get(pro_id, {})
        pro_nombre = pro_info.get("nombre", pro_id)
        nodos      = load_nodos_for_pro(pro_id) if pro_id else {}
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

        client   = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1024,
            system=system_prompt,
            messages=messages
        )
        return jsonify({"reply": response.content[0].text, "ready": True})

    except Exception as e:
        return jsonify({"reply": f"Error al conectar con el asistente: {str(e)}", "ready": False}), 500

# ── Feedback ──────────────────────────────────────────────────────────────────

@app.route("/api/feedback", methods=["POST"])
def save_feedback():
    data       = request.get_json(silent=True) or {}
    comentario = (data.get("comentario") or "").strip()
    if not comentario:
        return jsonify({"error": "comentario vacío"}), 400
    pantalla = (data.get("pantalla") or "Inicio")[:200]
    area_id  = (data.get("area_id")  or "")[:80]
    pro_id   = (data.get("pro_id")   or "")[:40]
    fid = str(uuid.uuid4())
    print(f"[feedback] USE_PG={USE_PG} DATABASE_URL_set={bool(DATABASE_URL)} DB_PATH={DB_PATH}")
    try:
        db_run(
            "INSERT INTO feedback (id, created_at, pantalla, area_id, pro_id, comentario) VALUES (?,?,?,?,?,?)",
            (fid, now_iso(), pantalla, area_id, pro_id, comentario)
        )
    except Exception as e:
        print(f"[feedback] DB ERROR: {e}")
        return jsonify({"error": str(e)}), 500
    print(f"[feedback] inserted id={fid}")
    return jsonify({"ok": True, "id": fid, "use_pg": USE_PG})

@app.route("/api/feedback")
def list_feedback():
    return jsonify(db_all("SELECT * FROM feedback ORDER BY created_at DESC"))

@app.route("/feedback")
def feedback_viewer():
    return render_template("feedback.html")

# ── Sessions ──────────────────────────────────────────────────────────────────

@app.route("/api/session", methods=["POST"])
def create_session():
    data    = request.get_json(silent=True) or {}
    pro_id  = data.get("pro_id",  "PRO141")
    area_id = data.get("area_id", "inventario")

    areas      = load_json(AREAS_PATH)
    first_node = areas["pros"].get(pro_id, {}).get("primer_nodo", "S0_alcance")

    sid = str(uuid.uuid4())
    ts  = now_iso()
    db_run(
        "INSERT INTO sessions (id, created_at, updated_at, estado, pro_id, area_id, current_node) VALUES (?,?,?,?,?,?,?)",
        (sid, ts, ts, "EN_CURSO", pro_id, area_id, first_node)
    )
    return jsonify({
        "session_id":   sid,
        "pro_id":       pro_id,
        "area_id":      area_id,
        "current_node": first_node,
        "estado":       "EN_CURSO"
    })

@app.route("/api/session/<sid>")
def get_session(sid):
    row = db_one("SELECT * FROM sessions WHERE id=?", (sid,))
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
    row  = db_one("SELECT * FROM sessions WHERE id=?", (sid,))
    if not row:
        return jsonify({"error": "not found"}), 404

    ts = now_iso()
    db_run("""
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
    return jsonify({"ok": True, "updated_at": ts})

@app.route("/api/session/<sid>/export")
def export_session(sid):
    row = db_one("SELECT * FROM sessions WHERE id=?", (sid,))
    if not row:
        return jsonify({"error": "not found"}), 404

    areas = load_json(AREAS_PATH)
    pro   = areas["pros"].get(row["pro_id"], {})
    payload = {
        "proceso":      f'{row["pro_id"]} – {pro.get("nombre", row["pro_id"])}',
        "session_id":   sid,
        "pro_id":       row["pro_id"],
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
    resp.headers["Content-Disposition"] = f'attachment; filename={row["pro_id"]}_{sid[:8]}.json'
    return resp

# Ejecutar init_db al importar (Vercel no llama __main__)
try:
    init_db()
except Exception as _e:
    print(f"[init_db] WARNING: {_e}")

if __name__ == "__main__":
    app.run(debug=True, port=5000)
