"""Repository para history_log — trazabilidad auditable de cada transición."""
import json
import uuid
import datetime
from database import get_connection


def _now():
    return datetime.datetime.now().isoformat(timespec="seconds")


class HistoryRepository:

    @staticmethod
    def append(
        instance_id: str,
        node_id: str,
        titulo: str,
        rol: str,
        inputs: dict,
        decision: int | None = None,
        decision_label: str | None = None,
        event_type: str = "TASK_COMPLETED",
    ) -> str:
        conn = get_connection()
        hid = str(uuid.uuid4())
        conn.execute(
            "INSERT INTO history_log "
            "(id, instance_id, node_id, titulo, rol, inputs, decision, "
            " decision_label, event_type, completed_at) "
            "VALUES (?,?,?,?,?,?,?,?,?,?)",
            (
                hid, instance_id, node_id, titulo, rol,
                json.dumps(inputs, ensure_ascii=False),
                decision, decision_label, event_type, _now(),
            ),
        )
        conn.commit()
        conn.close()
        return hid

    @staticmethod
    def list_for_instance(instance_id: str) -> list[dict]:
        conn = get_connection()
        rows = conn.execute(
            "SELECT * FROM history_log WHERE instance_id=? ORDER BY completed_at ASC",
            (instance_id,),
        ).fetchall()
        conn.close()
        result = []
        for r in rows:
            d = dict(r)
            d["inputs"] = json.loads(d["inputs"])
            result.append(d)
        return result
