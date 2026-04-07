"""
Configuración del Orquestador — Colbun S.A.
Roles, procedimientos, y settings de canales de notificación.
"""
import os

# ── Roles → Personas ─────────────────────────────────────────────────────────
# Placeholder: el usuario proporcionará emails @colbun.cl reales.
ROLE_CONTACTS = {
    "Operador de Turno": {
        "nombre": "Gustavo Bolívar",
        "email": "ep_gbolivar@colbun.cl",
    },
    "Jefe de Turno": {
        "nombre": "Gustavo Bolívar",
        "email": "ep_gbolivar@colbun.cl",
    },
    "Ingeniero de Turno": {
        "nombre": "R. Cornejo",
        "email": "rcornejo@colbun.cl",
    },
    "Operador COC": {
        "nombre": "R. Cornejo",
        "email": "rcornejo@colbun.cl",
    },
    "Despachador CDC": {
        "nombre": "Gustavo Bolívar (ext)",
        "email": "gustavo.bolivarggg@gmail.com",
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
