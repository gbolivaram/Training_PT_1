"""
EmailChannel — canal de notificación via email.
Soporta dos backends (en orden de prioridad):
  1. Resend API  → solo necesita RESEND_API_KEY (sin SMTP, sin 2FA)
  2. SMTP nativo → Gmail, Outlook/365, etc.
No requiere paquetes externos — usa urllib/smtplib de Python stdlib.
"""
import json
import smtplib
import ssl
import urllib.request
import urllib.error
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from config import (
    RESEND_API_KEY,
    SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, FROM_EMAIL,
)


def _build_html(titulo: str, mensaje: str, link: str) -> str:
    return f"""
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


class EmailChannel:

    @staticmethod
    def is_configured() -> bool:
        """Retorna True si al menos un backend de email está disponible."""
        return bool(RESEND_API_KEY) or bool(SMTP_USER and SMTP_PASSWORD)

    @staticmethod
    def send(to_email: str, to_name: str, titulo: str, mensaje: str, link: str) -> bool:
        # Prioridad 1: Resend API (más simple, sin SMTP/2FA)
        if RESEND_API_KEY:
            return EmailChannel._send_resend(to_email, to_name, titulo, mensaje, link)
        # Prioridad 2: SMTP nativo
        if SMTP_USER and SMTP_PASSWORD:
            return EmailChannel._send_smtp(to_email, to_name, titulo, mensaje, link)
        # Ninguno configurado
        print(f"[EmailChannel] Sin backend de email configurado — email a {to_email} no enviado")
        return False

    @staticmethod
    def _send_resend(to_email: str, to_name: str, titulo: str, mensaje: str, link: str) -> bool:
        """Envía email usando la API de Resend (urllib, sin deps externas)."""
        try:
            html = _build_html(titulo, mensaje, link)
            from_addr = FROM_EMAIL or "Orquestador Colbun <onboarding@resend.dev>"
            payload = json.dumps({
                "from": from_addr,
                "to": [to_email],
                "subject": titulo,
                "html": html,
            }).encode("utf-8")

            req = urllib.request.Request(
                "https://api.resend.com/emails",
                data=payload,
                headers={
                    "Authorization": f"Bearer {RESEND_API_KEY}",
                    "Content-Type": "application/json",
                },
                method="POST",
            )
            resp = urllib.request.urlopen(req, timeout=15)
            result = json.loads(resp.read().decode())
            print(f"[EmailChannel/Resend] Email enviado a {to_email}: {titulo} (id={result.get('id','')})")
            return True

        except urllib.error.HTTPError as e:
            body = e.read().decode() if e.fp else ""
            print(f"[EmailChannel/Resend] HTTP {e.code} enviando a {to_email}: {body}")
            return False
        except Exception as e:
            print(f"[EmailChannel/Resend] Error enviando a {to_email}: {e}")
            return False

    @staticmethod
    def _send_smtp(to_email: str, to_name: str, titulo: str, mensaje: str, link: str) -> bool:
        """Envía email usando SMTP nativo (Gmail, Outlook, etc.)."""
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = titulo
            msg["From"] = f"Orquestador Colbun <{FROM_EMAIL or SMTP_USER}>"
            msg["To"] = f"{to_name} <{to_email}>"

            text = f"{titulo}\n\n{mensaje}\n\nAcceda aquí: {link}"
            html = _build_html(titulo, mensaje, link)

            msg.attach(MIMEText(text, "plain"))
            msg.attach(MIMEText(html, "html"))

            context = ssl.create_default_context()
            with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10) as server:
                server.starttls(context=context)
                server.login(SMTP_USER, SMTP_PASSWORD)
                server.sendmail(FROM_EMAIL or SMTP_USER, to_email, msg.as_string())

            print(f"[EmailChannel/SMTP] Email enviado a {to_email}: {titulo}")
            return True

        except Exception as e:
            print(f"[EmailChannel/SMTP] Error enviando a {to_email}: {e}")
            return False
