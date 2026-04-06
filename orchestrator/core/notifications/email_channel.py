"""
EmailChannel — canal de notificación via email real (Resend API).
Activado cuando NOTIFICATION_MODE=email y RESEND_API_KEY está configurada.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from config import RESEND_API_KEY, FROM_EMAIL


class EmailChannel:

    @staticmethod
    def send(to_email: str, to_name: str, titulo: str, mensaje: str, link: str) -> bool:
        if not RESEND_API_KEY:
            return False
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
                    <p><a href="{link}"
                       style="background:#1a5276;color:white;padding:10px 20px;
                       text-decoration:none;border-radius:5px;">Ejecutar Tarea</a></p>
                """,
            })
            return True
        except Exception as e:
            print(f"[EmailChannel] Error: {e}")
            return False
