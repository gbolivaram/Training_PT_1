"""Repository para notifications — registros de notificación por actor."""
import uuid
import datetime
from database import get_connection


def _now():
    return datetime.datetime.now().isoformat(timespec="seconds")


class NotificationRepository:

    @staticmethod
    def create(
        instance_id: str, node_id: str, rol: str, titulo: str, mensaje: str,
        contact_name: str, contact_email: str, link: str, tipo: str = "TASK",
    ) -> str:
        conn = get_connection()
        nid = str(uuid.uuid4())
        conn.execute(
            "INSERT INTO notifications "
            "(id, instance_id, node_id, rol, contact_name, contact_email, "
            " titulo, mensaje, tipo, estado, link, created_at) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            (nid, instance_id, node_id, rol, contact_name, contact_email,
             titulo, mensaje, tipo, "PENDIENTE", link, _now()),
        )
        conn.commit()
        conn.close()
        return nid

    @staticmethod
    def mark(nid: str, estado: str, timestamp_field: str = "acted_at") -> None:
        conn = get_connection()
        conn.execute(
            f"UPDATE notifications SET estado=?, {timestamp_field}=? WHERE id=?",
            (estado, _now(), nid),
        )
        conn.commit()
        conn.close()

    @staticmethod
    def get(nid: str) -> dict | None:
        conn = get_connection()
        row = conn.execute("SELECT * FROM notifications WHERE id=?", (nid,)).fetchone()
        conn.close()
        return dict(row) if row else None

    @staticmethod
    def for_email(email: str) -> list[dict]:
        conn = get_connection()
        rows = conn.execute(
            "SELECT * FROM notifications WHERE contact_email=? ORDER BY created_at DESC",
            (email,),
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    @staticmethod
    def for_instance(instance_id: str) -> list[dict]:
        conn = get_connection()
        rows = conn.execute(
            "SELECT * FROM notifications WHERE instance_id=? ORDER BY created_at DESC",
            (instance_id,),
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    @staticmethod
    def all_pending() -> list[dict]:
        conn = get_connection()
        rows = conn.execute(
            "SELECT * FROM notifications WHERE estado='PENDIENTE' ORDER BY created_at DESC"
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]
