"""
NotificationDispatcher — activa al siguiente actor del proceso.

Las notificaciones NO son un efecto secundario: son el mecanismo
que mueve el sistema. Cuando se despacha una notificación, el
actor receptor queda activado para ejecutar su tarea.

Responsabilidades:
  - Crear registros en DB (Inbox UI)
  - (Futuro) Enviar email real vía Resend
  - Despachar alertas de STOP/BLOQUEO
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import models
from config import PROCEDURES, NOTIFICATION_MODE, RESEND_API_KEY, FROM_EMAIL
from core.transition_logic import resolve_contacts


def dispatch_to_actor(
    instance_id: str,
    pro_id: str,
    node_id: str,
    node: dict,
) -> list[str]:
    """
    Despacha notificaciones a todos los contactos del rol del nodo.
    Retorna la lista de notification_ids creados.

    Esta función ES el mecanismo que activa al siguiente actor.
    """
    rol = node.get("rol", "")
    contacts = resolve_contacts(rol)
    pro_nombre = PROCEDURES[pro_id]["nombre"]

    notif_ids = []
    for contact in contacts:
        link = f"/task/{instance_id}/{node_id}"
        titulo = f"[{pro_id}] {node.get('titulo', node_id)}"
        mensaje = (
            f"Se requiere su acción en el procedimiento {pro_id} — {pro_nombre}.\n\n"
            f"Tarea: {node.get('titulo', '')}\n"
            f"Descripción: {node.get('descripcion', '')}\n\n"
            f"Acceda al enlace para ejecutar esta tarea."
        )

        nid = models.create_notification(
            instance_id=instance_id,
            node_id=node_id,
            rol=rol,
            titulo=titulo,
            mensaje=mensaje,
            contact_name=contact["nombre"],
            contact_email=contact["email"],
            link=link,
        )
        notif_ids.append(nid)

        # Canal real: email vía Resend (activado con NOTIF_MODE=email)
        if NOTIFICATION_MODE == "email" and RESEND_API_KEY:
            _send_email(
                to_email=contact["email"],
                to_name=contact["nombre"],
                titulo=titulo,
                mensaje=mensaje,
                link=link,
            )

    return notif_ids


def dispatch_stop_alert(
    instance_id: str,
    pro_id: str,
    node_id: str,
    motivo: str,
    reported_by: str = "",
) -> list[str]:
    """
    Despacha alerta de STOP de emergencia a TODOS los roles definidos.
    Se usa cuando un actor activa la detención del proceso.
    """
    from config import ROLE_CONTACTS
    pro_nombre = PROCEDURES[pro_id]["nombre"]

    notif_ids = []
    for rol, contact in ROLE_CONTACTS.items():
        titulo = f"[STOP] {pro_id} detenido — {node_id}"
        mensaje = (
            f"PROCESO DETENIDO POR CONDICIÓN CRÍTICA\n\n"
            f"Procedimiento: {pro_id} — {pro_nombre}\n"
            f"Nodo: {node_id}\n"
            f"Motivo: {motivo}\n"
            f"Reportado por: {reported_by or 'N/A'}\n\n"
            f"Registre el motivo en SIGO y notifique al jefe de área."
        )
        nid = models.create_notification(
            instance_id=instance_id,
            node_id=node_id,
            rol=rol,
            titulo=titulo,
            mensaje=mensaje,
            contact_name=contact["nombre"],
            contact_email=contact["email"],
            link=f"/process/{instance_id}",
            tipo="STOP",
        )
        notif_ids.append(nid)

    return notif_ids


def _send_email(to_email: str, to_name: str, titulo: str, mensaje: str, link: str):
    """Envía email real vía Resend API."""
    try:
        import resend
        resend.api_key = RESEND_API_KEY
        resend.Emails.send({
            "from": FROM_EMAIL,
            "to": to_email,
            "subject": titulo,
            "html": f"""
                <h2>{titulo}</h2>
                <p>{mensaje.replace(chr(10), '<br>')}</p>
                <p><a href="{link}" style="background:#1a5276;color:white;padding:10px 20px;
                   text-decoration:none;border-radius:5px;">Ejecutar Tarea</a></p>
            """,
        })
    except Exception as e:
        print(f"[NotificationDispatcher] Email error: {e}")
