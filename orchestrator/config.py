"""
Configuración del Orquestador — Colbun S.A.
Roles, procedimientos, y settings de canales de notificación.
"""
import os

# ── Roles → Personas ─────────────────────────────────────────────────────────
# Placeholder: el usuario proporcionará emails @colbun.cl reales.
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

# ── Procedimientos ───────────────────────────────────────────────────────────
PROCEDURES = {
    "PRO115": {
        "nombre": "Procedimiento de Aviso de Falla en Instalaciones",
        "data_file": "pro115.json",
        "primer_nodo": "T1",
        "trigger_description": "Falla detectada en instalación",
    },
}

# ── Notificaciones ───────────────────────────────────────────────────────────
NOTIFICATION_MODE = os.environ.get("NOTIF_MODE", "web")  # "web" | "email"
RESEND_API_KEY = os.environ.get("RESEND_API_KEY")
FROM_EMAIL = os.environ.get("FROM_EMAIL", "orquestador@colbun.cl")
REMINDER_INTERVAL_MINUTES = int(os.environ.get("REMINDER_MINUTES", "30"))
