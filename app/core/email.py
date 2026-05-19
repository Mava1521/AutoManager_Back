"""
Módulo de Gestión de Correos Transaccionales.
"""

import logging
import smtplib
from abc import ABC, abstractmethod
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.core.config import settings

logger = logging.getLogger(__name__)

# ── Constantes Globales de Infraestructura ──────────────────────────────────
_SMTP_HOST = "smtp.gmail.com"
_SMTP_PORT = 465  # Puerto SSL estable
_TIMEOUT = 10
_SUPPORT_INBOX = "automanager.applications@gmail.com"


class EmailRenderer:
    """Encargado exclusivo de construir y formatear las vistas HTML corporativas."""

    @staticmethod
    def mask_email(email: str) -> str:
        """Anonimiza cuentas de correo en los logs para protección de datos."""
        try:
            local, domain = email.split("@")
            return f"{local[:2]}****@{domain}" if len(local) > 2 else f"****@{domain}"
        except ValueError:
            return "****"

    @staticmethod
    def render_recovery(to_name: str, reset_link: str) -> str:
        """Retorna la plantilla HTML para el flujo de restablecimiento."""
        return f"""
        <!DOCTYPE html>
        <html lang="es">
        <body style="margin:0; padding:0; background:#f4f6fb; font-family:Arial,sans-serif;">
          <table width="100%" cellpadding="0" cellspacing="0" style="padding:48px 16px;">
            <tr><td align="center">
              <table width="520" cellpadding="0" cellspacing="0" style="background:#ffffff; border-radius:16px; box-shadow:0 4px 24px rgba(0,36,156,0.10); overflow:hidden;">
                <tr>
                  <td style="background:linear-gradient(135deg,#00249C 0%,#40CEE4 100%); padding:36px 40px; text-align:center;">
                    <p style="margin:0; font-size:24px; font-weight:900; color:#ffffff; letter-spacing:2px;">AutoManager</p>
                    <p style="margin:6px 0 0; font-size:11px; font-weight:600; color:rgba(255,255,255,0.75); letter-spacing:3px; text-transform:uppercase;">Monitoring Innovation</p>
                  </td>
                </tr>
                <tr>
                  <td style="padding:40px;">
                    <p style="margin:0 0 10px; color:#222; font-size:16px; font-weight:700;">Hola, {to_name} 👋</p>
                    <p style="margin:0 0 10px; color:#555; font-size:14px; line-height:1.7;">Recibimos una solicitud para restablecer la contraseña de tu cuenta.</p>
                    <table width="100%" cellpadding="0" cellspacing="0" style="margin: 32px 0;">
                      <tr><td align="center"><a href="{reset_link}" style="display:inline-block; background:linear-gradient(90deg,#C6007E,#E280BE); color:#ffffff; text-decoration:none; font-size:15px; font-weight:700; padding:16px 44px; border-radius:30px; box-shadow:0 4px 14px rgba(198,0,126,0.35);">Restablecer contraseña →</a></td></tr>
                    </table>
                    <p style="margin:0; color:#bbb; font-size:12px; text-align:center; word-break:break-all;">¿El botón no funciona? Copia este enlace:<br/><a href="{reset_link}" style="color:#40CEE4; text-decoration:none;">{reset_link}</a></p>
                  </td>
                </tr>
              </table>
            </td></tr>
          </table>
        </body>
        </html>
        """

    @staticmethod
    def render_support_internal(sender_email: str, subject: str, body: str) -> str:
        """Retorna la plantilla del ticket técnico para el asesor."""
        body_html = body.replace("\n", "<br/>")
        return f"""
        <!DOCTYPE html>
        <html lang="es">
        <body style="margin:0; padding:0; background:#f4f6fb; font-family:Arial,sans-serif;">
          <table width="100%" cellpadding="0" cellspacing="0" style="padding:48px 16px;">
            <tr><td align="center">
              <table width="520" cellpadding="0" cellspacing="0" style="background:#ffffff; border-radius:16px; box-shadow:0 4px 24px rgba(0,36,156,0.10); overflow:hidden;">
                <tr>
                  <td style="background:linear-gradient(135deg,#00249C 0%,#40CEE4 100%); padding:28px 40px; text-align:center;">
                    <p style="margin:0; font-size:20px; font-weight:900; color:#ffffff; letter-spacing:2px;">🤖 AutoBot</p>
                    <p style="margin:6px 0 0; font-size:11px; font-weight:600; color:rgba(255,255,255,0.75); letter-spacing:3px; text-transform:uppercase;">Nueva consulta de soporte</p>
                  </td>
                </tr>
                <tr>
                  <td style="padding:32px 40px;">
                    <p style="margin:0 0 10px; color:#00249C; font-size:13px; font-weight:700;">Mensaje de <a href="mailto:{sender_email}">{sender_email}</a>:</p>
                    <div style="background:#f4f6fb; border-left:4px solid #40CEE4; padding:16px; color:#1a1a2e; font-size:14px; line-height:1.7;">{body_html}</div>
                  </td>
                </tr>
              </table>
            </td></tr>
          </table>
        </body>
        </html>
        """

    @staticmethod
    def render_user_confirmation(subject_consulta: str) -> str:
        """Retorna el acuse de recibo estético para el cliente."""
        return f"""
        <!DOCTYPE html>
        <html lang="es">
        <body style="margin:0; padding:0; background:#f4f6fb; font-family:Arial,sans-serif;">
          <table width="100%" cellpadding="0" cellspacing="0" style="padding:48px 16px;">
            <tr><td align="center">
              <table width="520" cellpadding="0" cellspacing="0" style="background:#ffffff; border-radius:16px; box-shadow:0 4px 24px rgba(0,36,156,0.10); overflow:hidden;">
                <tr>
                  <td style="background:linear-gradient(135deg,#00249C 0%,#40CEE4 100%); padding:36px 40px; text-align:center;">
                    <p style="margin:0; font-size:24px; font-weight:900; color:#ffffff;">AutoManager</p>
                    <p style="margin:6px 0 0; font-size:11px; font-weight:600; color:rgba(255,255,255,0.75); text-transform:uppercase;">Solicitud en Proceso</p>
                  </td>
                </tr>
                <tr>
                  <td style="padding:40px;">
                    <p style="margin:0 0 16px; color:#222; font-size:16px; font-weight:700;">¡Tu solicitud está en camino! ✉️</p>
                    <p style="color:#555; font-size:14px; line-height:1.7;">Hemos registrado tu ticket con el asunto: <strong>{subject_consulta}</strong>. Un asesor te responderá a la brevedad.</p>
                  </td>
                </tr>
              </table>
            </td></tr>
          </table>
        </body>
        </html>
        """


class BaseEmailProvider(ABC):
    """Interfaz abstracta que define el contrato mandatorio de mensajería."""

    @abstractmethod
    def send_recovery(self, to_email: str, to_name: str, reset_token: str) -> None:
        pass

    @abstractmethod
    def send_support(self, sender_email: str, subject: str, body: str) -> None:
        pass

    @abstractmethod
    def send_support_confirmation(self, to_email: str, subject_consulta: str) -> None:
        pass



class GmailSMTPProvider(BaseEmailProvider):
    """Proveedor de infraestructura basado en servidores seguros SMTP de Google."""

    def __init__(self):
        self.renderer = EmailRenderer()

    def _validate_config(self) -> None:
        if not settings.gmail_user or not settings.gmail_app_password:
            raise RuntimeError("[SMTP] Credenciales ausentes en variables de entorno (.env).")

    def _dispatch(self, to_address: str, message: MIMEMultipart) -> None:
        """Gestiona el ciclo de conexión física de red mediante SSL."""
        self._validate_config()
        try:
            with smtplib.SMTP_SSL(_SMTP_HOST, _SMTP_PORT, timeout=_TIMEOUT) as server:
                server.login(settings.gmail_user, settings.gmail_app_password)
                server.sendmail(settings.gmail_user, to_address, message.as_string())
        except smtplib.SMTPAuthenticationError as exc:
            logger.error("[SMTP Auth] Fallo crítico de autenticación en Google.")
            raise exc
        except smtplib.SMTPException as exc:
            logger.error("[SMTP Error] Error de protocolo de red hacia %s", self.renderer.mask_email(to_address))
            raise exc

    def send_recovery(self, to_email: str, to_name: str, reset_token: str) -> None:
        reset_link = f"{settings.frontend_url}/reset-password?token={reset_token}"
        
        msg = MIMEMultipart("alternative")
        msg["Subject"] = "Restablecer tu contraseña — AutoManager"
        msg["From"] = settings.email_display_name
        msg["To"] = to_email
        msg.attach(MIMEText(self.renderer.render_recovery(to_name, reset_link), "html", "utf-8"))

        logger.info("Despachando recuperación hacia: %s", self.renderer.mask_email(to_email))
        self._dispatch(to_email, msg)

    def send_support(self, sender_email: str, subject: str, body: str) -> None:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"[AutoManager Soporte] {subject}"
        msg["From"] = settings.email_display_name
        msg["To"] = _SUPPORT_INBOX
        msg["Reply-To"] = sender_email

        msg.attach(MIMEText(self.renderer.render_support_internal(sender_email, subject, body), "html", "utf-8"))

        logger.info("Despachando ticket de soporte de: %s al equipo interno", self.renderer.mask_email(sender_email))
        self._dispatch(_SUPPORT_INBOX, msg)

    def send_support_confirmation(self, to_email: str, subject_consulta: str) -> None:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = "Recibimos tu consulta — AutoManager"
        msg["From"] = settings.email_display_name
        msg["To"] = to_email

        msg.attach(MIMEText(self.renderer.render_user_confirmation(subject_consulta), "html", "utf-8"))

        logger.info("Despachando confirmación AutoBot hacia cliente: %s", self.renderer.mask_email(to_email))
        self._dispatch(to_email, msg)

_provider = GmailSMTPProvider()

def send_recovery_email(to_email: str, to_name: str, reset_token: str) -> None:
    _provider.send_recovery(to_email, to_name, reset_token)

def send_support_email(sender_email: str, subject: str, body: str) -> None:
    _provider.send_support(sender_email, subject, body)

def send_user_support_confirmation(to_email: str, subject_consulta: str) -> None:
    _provider.send_support_confirmation(to_email, subject_consulta)