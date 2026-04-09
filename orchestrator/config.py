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
NOTIFICATION_MODE = os.environ.get("NOTIF_MODE", "email")  # "web" | "email"

# ── SMTP (email nativo — funciona con Gmail, Outlook, cualquier SMTP) ────────
SMTP_HOST = os.environ.get("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USER = os.environ.get("SMTP_USER", "")          # ej: gustavo.bolivarggg@gmail.com
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")   # App Password de Gmail
FROM_EMAIL = os.environ.get("FROM_EMAIL", "")          # mismo que SMTP_USER

# Legacy (Resend ya no se usa)
RESEND_API_KEY = os.environ.get("RESEND_API_KEY")
REMINDER_INTERVAL_MINUTES = int(os.environ.get("REMINDER_MINUTES", "30"))
