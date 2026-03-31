"""
Configuración del Orquestador de Ejecución Operacional - Colbun S.A.
Mapeo de roles a personas/emails y settings de notificaciones.
"""
import os

# ── Mapeo de roles → personas ────────────────────────────────────────────────
# El usuario proporcionará emails reales para la prueba.
# Por ahora se usan placeholders.
ROLE_CONTACTS = {
    "Operador de Turno": {
        "nombre": "Operador Demo",
        "email": "operador@demo.colbun.cl",
    },
    "Jefe de Turno": {
        "nombre": "Jefe Turno Demo",
        "email": "jefeturno@demo.colbun.cl",
    },
    "Ingeniero de Turno": {
        "nombre": "Ingeniero Demo",
        "email": "ingeniero@demo.colbun.cl",
    },
    "Operador COC": {
        "nombre": "Operador COC Demo",
        "email": "coc@demo.colbun.cl",
    },
    "Despachador CDC": {
        "nombre": "Despachador Demo",
        "email": "cdc@demo.colbun.cl",
    },
}


def resolve_contacts(rol_string):
    """
    Dado un string de rol (ej: "Operador de Turno / Jefe de Turno"),
    devuelve la lista de contactos que deben ser notificados.
    """
    contacts = []
    roles = [r.strip() for r in rol_string.split("/")]
    for role in roles:
        for key, contact in ROLE_CONTACTS.items():
            if key.lower() in role.lower() or role.lower() in key.lower():
                if contact not in contacts:
                    contacts.append(contact)
                break
    return contacts


# ── Procedimientos disponibles ───────────────────────────────────────────────
PROCEDURES = {
    "PRO115": {
        "nombre": "Procedimiento de Aviso de Falla en Instalaciones",
        "data_file": "pro115.json",
        "primer_nodo": "T1",
        "trigger_description": "Falla detectada en instalación",
    },
}

# ── Notificaciones ───────────────────────────────────────────────────────────
NOTIFICATION_MODE = os.environ.get("NOTIF_MODE", "web")  # "web" o "email"
RESEND_API_KEY = os.environ.get("RESEND_API_KEY")
FROM_EMAIL = "orquestador@colbun.cl"
TIMEOUT_MINUTES = 30
