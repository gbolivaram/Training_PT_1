"""
Capa de base de datos — conexión y esquema.
Aislada del resto del sistema (Repository Pattern accede aquí).
"""
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "orchestrator.db")


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_schema():
    conn = get_connection()
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

        CREATE TABLE IF NOT EXISTS node_states (
            id              TEXT PRIMARY KEY,
            instance_id     TEXT NOT NULL,
            node_id         TEXT NOT NULL,
            estado          TEXT NOT NULL DEFAULT 'PENDING',
            started_at      TEXT NOT NULL,
            deadline_at     TEXT,
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
            event_type      TEXT NOT NULL DEFAULT 'TASK_COMPLETED',
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
