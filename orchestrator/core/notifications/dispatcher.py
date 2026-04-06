"""
NotificationDispatcher — enruta notificaciones a los canales configurados.
Las notificaciones SON el mecanismo de activación del siguiente actor.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from config import PROCEDURES, NOTIFICATION_MODE, ROLE_CONTACTS
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
        for contact in contacts:
            nid = InboxChannel.send(
                instance_id=instance_id, node_id=node_id, rol=rol,
                titulo=titulo, mensaje=mensaje,
                contact_name=contact["nombre"], contact_email=contact["email"],
                link=link,
            )
            notif_ids.append(nid)

            if NOTIFICATION_MODE == "email":
                EmailChannel.send(
                    to_email=contact["email"], to_name=contact["nombre"],
                    titulo=titulo, mensaje=mensaje, link=link,
                )

        return notif_ids

    @staticmethod
    def dispatch_stop(instance_id: str, pro_id: str, node_id: str,
                      motivo: str, reported_by: str = "") -> list[str]:
        """Alerta STOP a TODOS los roles del sistema."""
        pro_nombre = PROCEDURES[pro_id]["nombre"]

        notif_ids = []
        for rol, contact in ROLE_CONTACTS.items():
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
                contact_name=contact["nombre"], contact_email=contact["email"],
                link=f"/process/{instance_id}", tipo="STOP",
            )
            notif_ids.append(nid)
        return notif_ids
