"""
NotificationDispatcher — enruta notificaciones a los canales configurados.
Las notificaciones SON el mecanismo de activación del siguiente actor.
Siempre: Inbox (DB). Si SMTP configurado: también email.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from config import PROCEDURES, ROLE_CONTACTS
from core.state_machine.transitions import TransitionResolver
from core.notifications.inbox_channel import InboxChannel
from core.notifications.email_channel import EmailChannel


class NotificationDispatcher:

    @staticmethod
    def dispatch_task(instance_id: str, pro_id: str, node_id: str, node: dict) -> list[str]:
        """Activa a los actores del rol del nodo."""
        rol = node.get("rol", "")
        contacts = TransitionResolver.resolve_actor(rol)
        pro_nombre = PROCEDURES[pro_id]["nombre"]

        titulo = f"[{pro_id}] {node.get('titulo', node_id)}"
        mensaje = (
            f"Se requiere su acción en {pro_id} — {pro_nombre}.\n\n"
            f"Tarea: {node.get('titulo', '')}\n"
            f"Descripción: {node.get('descripcion', '')}\n\n"
            f"Acceda al enlace para ejecutar esta tarea."
        )
        link = f"/task/{instance_id}/{node_id}"

        notif_ids = []
        seen_emails = set()
        for contact in contacts:
            email = contact["email"]
            # Evitar duplicados (ej: Operador y Jefe de Turno son la misma persona)
            if email in seen_emails:
                continue
            seen_emails.add(email)

            nid = InboxChannel.send(
                instance_id=instance_id, node_id=node_id, rol=rol,
                titulo=titulo, mensaje=mensaje,
                contact_name=contact["nombre"], contact_email=email,
                link=link,
            )
            notif_ids.append(nid)

            # Siempre intentar email si SMTP está configurado
            if EmailChannel.is_configured():
                EmailChannel.send(
                    to_email=email, to_name=contact["nombre"],
                    titulo=titulo, mensaje=mensaje, link=link,
                )

        return notif_ids

    @staticmethod
    def dispatch_stop(instance_id: str, pro_id: str, node_id: str,
                      motivo: str, reported_by: str = "") -> list[str]:
        """Alerta STOP a TODOS los roles del sistema."""
        pro_nombre = PROCEDURES[pro_id]["nombre"]

        notif_ids = []
        seen_emails = set()
        for rol, contact in ROLE_CONTACTS.items():
            email = contact["email"]
            if email in seen_emails:
                continue
            seen_emails.add(email)

            titulo = f"[STOP] {pro_id} detenido — {node_id}"
            mensaje = (
                f"PROCESO DETENIDO POR CONDICIÓN CRÍTICA\n\n"
                f"Procedimiento: {pro_id} — {pro_nombre}\n"
                f"Nodo: {node_id}\nMotivo: {motivo}\n"
                f"Reportado por: {reported_by or 'N/A'}"
            )
            nid = InboxChannel.send(
                instance_id=instance_id, node_id=node_id, rol=rol,
                titulo=titulo, mensaje=mensaje,
                contact_name=contact["nombre"], contact_email=email,
                link=f"/process/{instance_id}", tipo="STOP",
            )
            notif_ids.append(nid)

            if EmailChannel.is_configured():
                EmailChannel.send(
                    to_email=email, to_name=contact["nombre"],
                    titulo=titulo, mensaje=mensaje, link=f"/process/{instance_id}",
                )

        return notif_ids
