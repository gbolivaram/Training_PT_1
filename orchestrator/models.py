"""
Modelos de datos del orquestador.
Usa SQLite para persistencia local.
"""
import sqlite3
import json
import uuid
import datetime
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "orchestrator.db")


def now_iso():
    return datetime.datetime.now().isoformat(timespec="seconds")


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS process_instances (
            id              TEXT PRIMARY KEY,
            pro_id          TEXT NOT NULL,
            trigger_event   TEXT NOT NULL DEFAULT '',
            current_node    TEXT NOT NULL,
            estado          TEXT NOT NULL DEFAULT 'EN_CURSO',
            inputs          TEXT NOT NULL DEFAULT '{}',
            history         TEXT NOT NULL DEFAULT '[]',
            created_at      TEXT NOT NULL,
            updated_at      TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS notifications (
            id              TEXT PRIMARY KEY,
            instance_id     TEXT NOT NULL,
            node_id         TEXT NOT NULL,
            rol             TEXT NOT NULL,
            contact_name    TEXT NOT NULL DEFAULT '',
            contact_email   TEXT NOT NULL DEFAULT '',
            titulo          TEXT NOT NULL,
            mensaje         TEXT NOT NULL DEFAULT '',
            estado          TEXT NOT NULL DEFAULT 'PENDIENTE',
            link            TEXT NOT NULL DEFAULT '',
            created_at      TEXT NOT NULL,
            read_at         TEXT,
            acted_at        TEXT,
            FOREIGN KEY (instance_id) REFERENCES process_instances(id)
        );
    """)
    conn.commit()
    conn.close()


# ── Process Instances ────────────────────────────────────────────────────────

def create_instance(pro_id, primer_nodo, trigger_event=""):
    conn = get_db()
    iid = str(uuid.uuid4())
    ts = now_iso()
    conn.execute(
        "INSERT INTO process_instances (id, pro_id, trigger_event, current_node, estado, created_at, updated_at) VALUES (?,?,?,?,?,?,?)",
        (iid, pro_id, trigger_event, primer_nodo, "EN_CURSO", ts, ts),
    )
    conn.commit()
    conn.close()
    return iid


def get_instance(iid):
    conn = get_db()
    row = conn.execute("SELECT * FROM process_instances WHERE id=?", (iid,)).fetchone()
    conn.close()
    if not row:
        return None
    d = dict(row)
    d["inputs"] = json.loads(d["inputs"])
    d["history"] = json.loads(d["history"])
    return d


def update_instance(iid, **kwargs):
    conn = get_db()
    sets = ["updated_at=?"]
    vals = [now_iso()]
    for k, v in kwargs.items():
        if k in ("inputs", "history"):
            v = json.dumps(v, ensure_ascii=False)
        sets.append(f"{k}=?")
        vals.append(v)
    vals.append(iid)
    conn.execute(f"UPDATE process_instances SET {', '.join(sets)} WHERE id=?", vals)
    conn.commit()
    conn.close()


def list_instances():
    conn = get_db()
    rows = conn.execute("SELECT * FROM process_instances ORDER BY created_at DESC").fetchall()
    conn.close()
    result = []
    for row in rows:
        d = dict(row)
        d["inputs"] = json.loads(d["inputs"])
        d["history"] = json.loads(d["history"])
        result.append(d)
    return result


# ── Notifications ────────────────────────────────────────────────────────────

def create_notification(instance_id, node_id, rol, titulo, mensaje, contact_name, contact_email, link):
    conn = get_db()
    nid = str(uuid.uuid4())
    ts = now_iso()
    conn.execute(
        "INSERT INTO notifications (id, instance_id, node_id, rol, contact_name, contact_email, titulo, mensaje, estado, link, created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        (nid, instance_id, node_id, rol, contact_name, contact_email, titulo, mensaje, "PENDIENTE", link, ts),
    )
    conn.commit()
    conn.close()
    return nid


def get_notifications_for_email(email):
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM notifications WHERE contact_email=? ORDER BY created_at DESC", (email,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_notifications_for_instance(instance_id):
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM notifications WHERE instance_id=? ORDER BY created_at DESC", (instance_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_notification(nid):
    conn = get_db()
    row = conn.execute("SELECT * FROM notifications WHERE id=?", (nid,)).fetchone()
    conn.close()
    return dict(row) if row else None


def mark_notification(nid, estado, timestamp_field="acted_at"):
    conn = get_db()
    conn.execute(
        f"UPDATE notifications SET estado=?, {timestamp_field}=? WHERE id=?",
        (estado, now_iso(), nid),
    )
    conn.commit()
    conn.close()


def get_all_pending_notifications():
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM notifications WHERE estado='PENDIENTE' ORDER BY created_at DESC"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]
