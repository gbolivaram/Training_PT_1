"""
TransitionLogic — lógica pura de transiciones.

SIN acceso a DB. Recibe nodos del procedimiento JSON y retorna
el siguiente nodo y los contactos del siguiente actor.

Responsabilidades:
  - Dado un nodo + decisión → siguiente node_id
  - Dado un rol string     → lista de contactos a notificar
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from config import ROLE_CONTACTS


def resolve_next(node: dict, decision: int | None = None) -> str | None:
    """
    Determina el node_id siguiente según el tipo de nodo.

      task     → node["next"]
      decision → node["opciones"][decision]["next"]
      end      → None  (proceso terminado)
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
                f"Decisión inválida: {decision} (opciones disponibles: 0-{len(opciones)-1})"
            )
        return opciones[decision]["next"]

    return None


def resolve_contacts(rol_string: str) -> list[dict]:
    """
    Dado un string de rol compuesto (ej: "Jefe de Turno / Operador COC"),
    retorna la lista de contactos {nombre, email} que deben ser notificados.

    Usa matching exacto primero, luego parcial como fallback.
    """
    contacts = []
    seen_emails = set()

    roles = [r.strip() for r in rol_string.split("/")]

    for role in roles:
        role_lower = role.lower()
        matched = None

        # Primero: match exacto
        if role in ROLE_CONTACTS:
            matched = ROLE_CONTACTS[role]
        else:
            # Fallback: match parcial (el key está contenido en el rol o viceversa)
            for key, contact in ROLE_CONTACTS.items():
                if key.lower() == role_lower or key.lower() in role_lower:
                    matched = contact
                    break

        if matched and matched["email"] not in seen_emails:
            contacts.append(matched)
            seen_emails.add(matched["email"])

    return contacts


def is_stop_allowed(node: dict) -> bool:
    """Indica si el nodo permite una detención de emergencia."""
    return node.get("allow_stop", False)


def get_decision_label(node: dict, decision: int) -> str:
    """Retorna el label de la opción elegida en un nodo de decisión."""
    opciones = node.get("opciones", [])
    if 0 <= decision < len(opciones):
        return opciones[decision].get("label", str(decision))
    return str(decision)
