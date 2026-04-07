"""Repository para node_states — estado de cada nodo en una instancia."""
import uuid
import datetime
from database import get_connection


def _now():
    return datetime.datetime.now().isoformat(timespec="seconds")


def _deadline(minutes: int | None) -> str | None:
    if not minutes:
        return None
    return (datetime.datetime.now() + datetime.timedelta(minutes=minutes)).isoformat(timespec="seconds")


class NodeStateRepository:

    @staticmethod
    def create(instance_id: str, node_id: str, estado: str = "IN_PROGRESS",
               deadline_minutes: int | None = None) -> str:
        conn = get_connection()
        nsid = str(uuid.uuid4())
        conn.execute(
            "INSERT INTO node_states (id, instance_id, node_id, estado, started_at, deadline_at) "
            "VALUES (?,?,?,?,?,?)",
            (nsid, instance_id, node_id, estado, _now(), _deadline(deadline_minutes)),
        )
        conn.commit()
        conn.close()
        return nsid

    @staticmethod
    def update(instance_id: str, node_id: str, estado: str) -> None:
        conn = get_connection()
        completed = _now() if estado in ("COMPLETED", "STOPPED", "BLOCKED") else None
        conn.execute(
            "UPDATE node_states SET estado=?, completed_at=? "
            "WHERE instance_id=? AND node_id=? AND id=("
            "  SELECT id FROM node_states WHERE instance_id=? AND node_id=? "
            "  ORDER BY started_at DESC LIMIT 1"
            ")",
            (estado, completed, instance_id, node_id, instance_id, node_id),
        )
        conn.commit()
        conn.close()

    @staticmethod
    def list_for_instance(instance_id: str) -> list[dict]:
        conn = get_connection()
        rows = conn.execute(
            "SELECT * FROM node_states WHERE instance_id=? ORDER BY started_at ASC",
            (instance_id,),
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    @staticmethod
    def overdue() -> list[dict]:
        """Retorna nodos IN_PROGRESS cuyo deadline_at ya pasó."""
        conn = get_connection()
        rows = conn.execute(
            "SELECT ns.*, pi.pro_id FROM node_states ns "
            "JOIN process_instances pi ON pi.id = ns.instance_id "
            "WHERE ns.estado = 'IN_PROGRESS' "
            "AND ns.deadline_at IS NOT NULL "
            "AND ns.deadline_at < ? "
            "ORDER BY ns.deadline_at ASC",
            (_now(),),
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    @staticmethod
    def active_with_deadline() -> list[dict]:
        """Retorna todos los nodos IN_PROGRESS con deadline (vencido o no)."""
        conn = get_connection()
        rows = conn.execute(
            "SELECT ns.*, pi.pro_id FROM node_states ns "
            "JOIN process_instances pi ON pi.id = ns.instance_id "
            "WHERE ns.estado = 'IN_PROGRESS' "
            "AND ns.deadline_at IS NOT NULL "
            "ORDER BY ns.deadline_at ASC",
            (),
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]
