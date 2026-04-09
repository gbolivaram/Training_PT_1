"""
EmailChannel — canal de notificación via email real (SMTP nativo).
Funciona con cualquier servidor SMTP: Gmail, Outlook/365, Colbun, etc.
No requiere paquetes externos — usa smtplib de Python.
"""
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from config import SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, FROM_EMAIL


class EmailChannel:

    @staticmethod
    def send(to_email: str, to_name: str, titulo: str, mensaje: str, link: str) -> bool:
        if not SMTP_HOST or not SMTP_USER or not SMTP_PASSWORD:
            print(f"[EmailChannel] SMTP no configurado — email a {to_email} no enviado")
            return False

        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = titulo
            msg["From"] = f"Orquestador Colbun <{FROM_EMAIL}>"
            msg["To"] = f"{to_name} <{to_email}>"

            # Versión texto plano
            text = f"{titulo}\n\n{mensaje}\n\nAcceda aquí: {link}"

            # Versión HTML
            html = f"""
            <div style="font-family: -apple-system, sans-serif; max-width:600px; margin:0 auto;">
                <div style="background:#1a5276; color:white; padding:15px 20px; border-radius:8px 8px 0 0;">
                    <h2 style="margin:0; font-size:16px;">{titulo}</h2>
                </div>
                <div style="padding:20px; border:1px solid #dce1e6; border-top:none; border-radius:0 0 8px 8px;">
                    <p style="white-space:pre-line; color:#2c3e50; line-height:1.6;">{mensaje}</p>
                    <div style="margin-top:20px; text-align:center;">
                        <a href="{link}"
                           style="background:#1a5276; color:white; padding:12px 24px;
                           text-decoration:none; border-radius:5px; font-weight:bold;
                           display:inline-block;">
                            Ejecutar Tarea
                        </a>
                    </div>
                    <p style="margin-top:20px; font-size:12px; color:#7f8c8d;">
                        Este es un mensaje automático del Orquestador de Ejecución Operacional — Colbun S.A.
                    </p>
                </div>
            </div>
            """

            msg.attach(MIMEText(text, "plain"))
            msg.attach(MIMEText(html, "html"))

            context = ssl.create_default_context()
            with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10) as server:
                server.starttls(context=context)
                server.login(SMTP_USER, SMTP_PASSWORD)
                server.sendmail(FROM_EMAIL, to_email, msg.as_string())

            print(f"[EmailChannel] Email enviado a {to_email}: {titulo}")
            return True

        except Exception as e:
            print(f"[EmailChannel] Error enviando a {to_email}: {e}")
            return False
