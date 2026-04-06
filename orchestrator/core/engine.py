"""
Orchestrator Engine — punto de entrada para todas las operaciones del sistema.

Coordina:
  - Recibe commands desde la API
  - Ejecuta commands (que usan State Machine + Repository internamente)
  - Los commands publican eventos al EventBus
  - Los handlers (observers) reaccionan: notifican actores, registran auditoría

Stack:
  API → Command → Orchestrator → State Machine → Repository → EventBus → Handlers
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from core.events.bus import EventBus
from core.events.handlers import notification_handler, audit_handler
from core.commands.base import CommandError
from core.commands.trigger_process import TriggerProcessCommand
from core.commands.complete_task import CompleteTaskCommand
from core.commands.stop_process import StopProcessCommand
from core.commands.block_process import BlockProcessCommand, UnblockProcessCommand
from config import PROCEDURES

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")

# ── Loader de procedimientos ─────────────────────────────────────────────────

def load_procedure(pro_id: str) -> dict:
    """Carga el JSON de un procedimiento desde disco."""
    proc = PROCEDURES.get(pro_id)
    if not proc:
        raise ValueError(f"Procedimiento '{pro_id}' no registrado.")
    path = os.path.join(DATA_DIR, proc["data_file"])
    with open(path, encoding="utf-8") as f:
        return json.load(f)


# ── Setup del EventBus (registra handlers una sola vez) ──────────────────────

_bus_initialized = False

def _ensure_bus():
    global _bus_initialized
    if not _bus_initialized:
        bus = EventBus()
        notification_handler.register(bus)
        audit_handler.register(bus)
        _bus_initialized = True


# ── Orchestrator: fachada pública ────────────────────────────────────────────

class Orchestrator:
    """
    Fachada que recibe acciones y las delega a Commands.
    La API llama exclusivamente a este objeto.
    """

    @staticmethod
    def trigger(pro_id: str, trigger_event: str = "Manual") -> dict:
        _ensure_bus()
        cmd = TriggerProcessCommand(pro_id, trigger_event)
        try:
            return cmd.execute()
        except CommandError as e:
            return {"error": str(e)}

    @staticmethod
    def complete(instance_id: str, node_id: str,
                 inputs: dict | None = None, decision: int | None = None) -> dict:
        _ensure_bus()
        cmd = CompleteTaskCommand(instance_id, node_id, inputs, decision)
        try:
            return cmd.execute()
        except CommandError as e:
            return {"error": str(e)}

    @staticmethod
    def stop(instance_id: str, node_id: str, motivo: str, reported_by: str = "") -> dict:
        _ensure_bus()
        cmd = StopProcessCommand(instance_id, node_id, motivo, reported_by)
        try:
            return cmd.execute()
        except CommandError as e:
            return {"error": str(e)}

    @staticmethod
    def block(instance_id: str, node_id: str, motivo: str) -> dict:
        _ensure_bus()
        cmd = BlockProcessCommand(instance_id, node_id, motivo)
        try:
            return cmd.execute()
        except CommandError as e:
            return {"error": str(e)}

    @staticmethod
    def unblock(instance_id: str) -> dict:
        _ensure_bus()
        cmd = UnblockProcessCommand(instance_id)
        try:
            return cmd.execute()
        except CommandError as e:
            return {"error": str(e)}
