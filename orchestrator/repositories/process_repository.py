"""Repository para process_instances — acceso a datos de instancias de proceso."""
import json
import uuid
import datetime
from database import get_connection


def _now():
    return datetime.datetime.now().isoformat(timespec="seconds")


class ProcessRepository:

    @staticmethod
    def create(pro_id: str, primer_nodo: str, trigger_event: str = "") -> str:
        conn = get_connection()
        pid = str(uuid.uuid4())
        ts = _now()
        conn.execute(
            "INSERT INTO process_instances "
            "(id, pro_id, trigger_event, current_node, estado, created_at, updated_at) "
            "VALUES (?,?,?,?,?,?,?)",
            (pid, pro_id, trigger_event, primer_nodo, "EN_CURSO", ts, ts),
        )
        conn.commit()
        conn.close()
        return pid

    @staticmethod
    def get(pid: str) -> dict | None:
        conn = get_connection()
        row = conn.execute("SELECT * FROM process_instances WHERE id=?", (pid,)).fetchone()
        conn.close()
        if not row:
            return None
        d = dict(row)
        d["inputs"] = json.loads(d["inputs"])
        return d

    @staticmethod
    def update(pid: str, **kwargs) -> None:
        conn = get_connection()
        sets = ["updated_at=?"]
        vals = [_now()]
        for k, v in kwargs.items():
            if k == "inputs":
                v = json.dumps(v, ensure_ascii=False)
            sets.append(f"{k}=?")
            vals.append(v)
        vals.append(pid)
        conn.execute(f"UPDATE process_instances SET {', '.join(sets)} WHERE id=?", vals)
        conn.commit()
        conn.close()

    @staticmethod
    def list_all() -> list[dict]:
        conn = get_connection()
        rows = conn.execute(
            "SELECT * FROM process_instances ORDER BY created_at DESC"
        ).fetchall()
        conn.close()
        return [{**dict(r), "inputs": json.loads(r["inputs"])} for r in rows]
