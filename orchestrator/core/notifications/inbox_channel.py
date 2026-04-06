"""
InboxChannel — canal de notificación via base de datos (Inbox UI web).
Crea un registro en la tabla notifications que el actor ve en su bandeja.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from repositories.notification_repository import NotificationRepository


class InboxChannel:

    @staticmethod
    def send(instance_id: str, node_id: str, rol: str, titulo: str,
             mensaje: str, contact_name: str, contact_email: str,
             link: str, tipo: str = "TASK") -> str:
        return NotificationRepository.create(
            instance_id=instance_id,
            node_id=node_id,
            rol=rol,
            titulo=titulo,
            mensaje=mensaje,
            contact_name=contact_name,
            contact_email=contact_email,
            link=link,
            tipo=tipo,
        )
