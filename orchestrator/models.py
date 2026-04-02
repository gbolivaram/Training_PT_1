"""
Capa de datos del Orquestador — Colbun S.A.

Tablas:
  process_instances  → una fila por instancia de procedimiento activa
  node_state         → estado de cada nodo en cada instancia (trazabilidad)
  history_log        → registro auditable de cada transición con timestamp
  notifications      → notificaciones por actor (Inbox UI + email futuro)
"""
import sqlite3
import json
import uuid
import datetime
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "orchestrator.db")


def now_iso() -> str:
    return datetime.datetime.now().isoformat(timespec="seconds")


def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")   # evita race conditions básicas
    conn.execute("PRAGMA foreign_keys=ON")
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
            created_at      TEXT NOT NULL,
            updated_at      TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS node_state (
            id              TEXT PRIMARY KEY,
            instance_id     TEXT NOT NULL,
            node_id         TEXT NOT NULL,
            estado          TEXT NOT NULL DEFAULT 'IN_PROGRESS',
            started_at      TEXT NOT NULL,
            completed_at    TEXT,
            FOREIGN KEY (instance_id) REFERENCES process_instances(id)
        );

        CREATE TABLE IF NOT EXISTS history_log (
            id              TEXT PRIMARY KEY,
            instance_id     TEXT NOT NULL,
            node_id         TEXT NOT NULL,
            titulo          TEXT NOT NULL DEFAULT '',
            rol             TEXT NOT NULL DEFAULT '',
            inputs          TEXT NOT NULL DEFAULT '{}',
            decision        INTEGER,
            decision_label  TEXT,
            completed_at    TEXT NOT NULL,
            FOREIGN KEY (instance_id) REFERENCES process_instances(id)
        );

        CREATE TABLE IF NOT EXISTS notifications (
            id              TEXT PRIMARY KEY,
            instance_id     TEXT NOT NULL,
            node_id         TEXT NOT NULL,
            rol             TEXT NOT NULL DEFAULT '',
            contact_name    TEXT NOT NULL DEFAULT '',
            contact_email   TEXT NOT NULL DEFAULT '',
            titulo          TEXT NOT NULL,
            mensaje         TEXT NOT NULL DEFAULT '',
            tipo            TEXT NOT NULL DEFAULT 'TASK',
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


# ── process_instances ────────────────────────────────────────────────────────

def create_instance(pro_id: str, primer_nodo: str, trigger_event: str = "") -> str:
    conn = get_db()
    iid = str(uuid.uuid4())
    ts = now_iso()
    conn.execute(
        "INSERT INTO process_instances (id, pro_id, trigger_event, current_node, estado, created_at, updated_at) "
        "VALUES (?,?,?,?,?,?,?)",
        (iid, pro_id, trigger_event, primer_nodo, "EN_CURSO", ts, ts),
    )
    conn.commit()
    conn.close()
    return iid


def get_instance(iid: str) -> dict | None:
    conn = get_db()
    row = conn.execute("SELECT * FROM process_instances WHERE id=?", (iid,)).fetchone()
    conn.close()
    if not row:
        return None
    d = dict(row)
    d["inputs"] = json.loads(d["inputs"])
    return d


def update_instance(iid: str, **kwargs) -> None:
    conn = get_db()
    sets = ["updated_at=?"]
    vals = [now_iso()]
    for k, v in kwargs.items():
        if k == "inputs":
            v = json.dumps(v, ensure_ascii=False)
        sets.append(f"{k}=?")
        vals.append(v)
    vals.append(iid)
    conn.execute(f"UPDATE process_instances SET {', '.join(sets)} WHERE id=?", vals)
    conn.commit()
    conn.close()


def list_instances() -> list[dict]:
    conn = get_db()
    rows = conn.execute("SELECT * FROM process_instances ORDER BY created_at DESC").fetchall()
    conn.close()
    result = []
    for row in rows:
        d = dict(row)
        d["inputs"] = json.loads(d["inputs"])
        result.append(d)
    return result


# ── node_state ───────────────────────────────────────────────────────────────

def create_node_state(instance_id: str, node_id: str, estado: str = "IN_PROGRESS") -> str:
    conn = get_db()
    nsid = str(uuid.uuid4())
    conn.execute(
        "INSERT INTO node_state (id, instance_id, node_id, estado, started_at) VALUES (?,?,?,?,?)",
        (nsid, instance_id, node_id, estado, now_iso()),
    )
    conn.commit()
    conn.close()
    return nsid


def update_node_state(instance_id: str, node_id: str, estado: str) -> None:
    """Actualiza el estado del nodo más reciente de esa instancia."""
    conn = get_db()
    ts = now_iso() if estado in ("COMPLETED", "STOPPED", "BLOCKED") else None
    conn.execute(
        "UPDATE node_state SET estado=?, completed_at=? "
        "WHERE instance_id=? AND node_id=? AND id=("
        "  SELECT id FROM node_state WHERE instance_id=? AND node_id=? "
        "  ORDER BY started_at DESC LIMIT 1"
        ")",
        (estado, ts, instance_id, node_id, instance_id, node_id),
    )
    conn.commit()
    conn.close()


def get_node_states(instance_id: str) -> list[dict]:
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM node_state WHERE instance_id=? ORDER BY started_at ASC",
        (instance_id,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ── history_log ───────────────────────────────────────────────────────────────

def append_history_log(
    instance_id: str,
    node_id: str,
    titulo: str,
    rol: str,
    inputs: dict,
    decision: int | None,
    decision_label: str | None,
) -> str:
    conn = get_db()
    hid = str(uuid.uuid4())
    conn.execute(
        "INSERT INTO history_log "
        "(id, instance_id, node_id, titulo, rol, inputs, decision, decision_label, completed_at) "
        "VALUES (?,?,?,?,?,?,?,?,?)",
        (
            hid, instance_id, node_id, titulo, rol,
            json.dumps(inputs, ensure_ascii=False),
            decision, decision_label, now_iso(),
        ),
    )
    conn.commit()
    conn.close()
    return hid


def get_history_log(instance_id: str) -> list[dict]:
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM history_log WHERE instance_id=? ORDER BY completed_at ASC",
        (instance_id,),
    ).fetchall()
    conn.close()
    result = []
    for row in rows:
        d = dict(row)
        d["inputs"] = json.loads(d["inputs"])
        result.append(d)
    return result


# ── notifications ────────────────────────────────────────────────────────────

def create_notification(
    instance_id: str, node_id: str, rol: str, titulo: str, mensaje: str,
    contact_name: str, contact_email: str, link: str, tipo: str = "TASK",
) -> str:
    conn = get_db()
    nid = str(uuid.uuid4())
    conn.execute(
        "INSERT INTO notifications "
        "(id, instance_id, node_id, rol, contact_name, contact_email, "
        " titulo, mensaje, tipo, estado, link, created_at) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
        (nid, instance_id, node_id, rol, contact_name, contact_email,
         titulo, mensaje, tipo, "PENDIENTE", link, now_iso()),
    )
    conn.commit()
    conn.close()
    return nid


def get_notifications_for_email(email: str) -> list[dict]:
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM notifications WHERE contact_email=? ORDER BY created_at DESC", (email,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_notifications_for_instance(instance_id: str) -> list[dict]:
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM notifications WHERE instance_id=? ORDER BY created_at DESC", (instance_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_notification(nid: str) -> dict | None:
    conn = get_db()
    row = conn.execute("SELECT * FROM notifications WHERE id=?", (nid,)).fetchone()
    conn.close()
    return dict(row) if row else None


def mark_notification(nid: str, estado: str, timestamp_field: str = "acted_at") -> None:
    conn = get_db()
    conn.execute(
        f"UPDATE notifications SET estado=?, {timestamp_field}=? WHERE id=?",
        (estado, now_iso(), nid),
    )
    conn.commit()
    conn.close()


def get_all_pending_notifications() -> list[dict]:
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM notifications WHERE estado='PENDIENTE' ORDER BY created_at DESC"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]
