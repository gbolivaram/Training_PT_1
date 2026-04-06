"""
TransitionResolver — lógica pura para resolver transiciones del procedimiento.

SIN acceso a DB. Opera sobre los nodos del JSON.
Determina: siguiente nodo, actor(es) responsable(s), si se permite STOP.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from config import ROLE_CONTACTS


class TransitionResolver:
    """Resuelve transiciones entre nodos del procedimiento."""

    @staticmethod
    def next_node(node: dict, decision: int | None = None) -> str | None:
        """
        Dado un nodo + decisión opcional, retorna el node_id siguiente.
        Retorna None si el nodo es terminal (type=end).
        """
        node_type = node.get("type", "task")

        if node_type == "end":
            return None
        if node_type == "task":
            return node.get("next")
        if node_type == "decision":
            opciones = node.get("opciones", [])
            if decision is None or not (0 <= decision < len(opciones)):
                raise ValueError(
                    f"Decisión inválida: {decision} (hay {len(opciones)} opciones)"
                )
            return opciones[decision]["next"]
        return None

    @staticmethod
    def resolve_actor(rol_string: str) -> list[dict]:
        """
        Dado un string de rol, retorna los contactos que deben ser activados.
        Soporta roles compuestos ("Rol A / Rol B").
        """
        contacts = []
        seen = set()
        for role in (r.strip() for r in rol_string.split("/")):
            role_lower = role.lower()
            # Match exacto primero
            if role in ROLE_CONTACTS:
                c = ROLE_CONTACTS[role]
                if c["email"] not in seen:
                    contacts.append(c)
                    seen.add(c["email"])
                continue
            # Fallback parcial
            for key, c in ROLE_CONTACTS.items():
                if key.lower() in role_lower or role_lower in key.lower():
                    if c["email"] not in seen:
                        contacts.append(c)
                        seen.add(c["email"])
                    break
        return contacts

    @staticmethod
    def allows_stop(node: dict) -> bool:
        return node.get("allow_stop", False)

    @staticmethod
    def decision_label(node: dict, decision: int) -> str:
        opciones = node.get("opciones", [])
        if 0 <= decision < len(opciones):
            return opciones[decision].get("label", str(decision))
        return str(decision)

    @staticmethod
    def is_end_node(node: dict) -> bool:
        return node.get("type") == "end"
