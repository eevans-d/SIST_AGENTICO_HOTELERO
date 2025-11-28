# [PROMPT 2.4 + E.1] app/services/gmail_client.py

import imaplib
import smtplib
import email
from email.message import Message
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import decode_header
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
import structlog

from ..core.settings import settings
from ..exceptions.pms_exceptions import PMSError
from ..core.correlation import get_correlation_id

logger = structlog.get_logger(__name__)


class GmailClientError(PMSError):
    """Base exception for Gmail client errors"""

    pass


class GmailAuthError(GmailClientError):
    """Gmail authentication failed"""

    pass


class GmailConnectionError(GmailClientError):
    """Gmail connection failed"""

    pass


class GmailIMAPClient:
    """
    Gmail IMAP/SMTP client for email communication.

    Features:
    - IMAP polling for new messages
    - SMTP sending with proper authentication
    - Timeout configuration for resilience
    - Structured logging for observability

    Usage:
        client = GmailIMAPClient()
        messages = await client.poll_new_messages()
        await client.send_response("guest@example.com", "Confirmación", "Tu reserva...")
    """

    def __init__(self):
        self.imap_server = "imap.gmail.com"
        self.smtp_server = "smtp.gmail.com"
        self.imap_port = 993  # SSL
        self.smtp_port = 465  # SSL
        self.username = settings.gmail_username
        self.password = settings.gmail_app_password.get_secret_value()

        # Configurar timeout para sockets IMAP/SMTP
        self.socket_timeout = 30.0  # 30 segundos para operaciones IMAP/SMTP

        logger.info(
            "gmail.client.initialized",
            extra={
                "username": self.username,
                "imap_server": self.imap_server,
                "smtp_server": self.smtp_server,
            },
        )

    def poll_new_messages(self, folder: str = "INBOX", mark_read: bool = True) -> List[Dict[str, Any]]:
        """
        Poll for new unread messages via IMAP.

        Args:
            folder: IMAP folder to check (default: INBOX)
            mark_read: Mark messages as read after fetching

        Returns:
            List of email dictionaries with structure:
            {
                "message_id": str,
                "from": str,
                "subject": str,
                "body": str,
                "timestamp": str (ISO 8601),
                "raw_email": email.message.Message
            }

        Raises:
            GmailAuthError: Authentication failed
            GmailConnectionError: Connection failed
            GmailClientError: Other IMAP errors
        """
        messages = []
        mail = None

        try:
            # Conectar con timeout
            logger.debug("gmail.imap.connecting", extra={"server": self.imap_server})
            mail = imaplib.IMAP4_SSL(self.imap_server, self.imap_port, timeout=self.socket_timeout)

            # Autenticar
            logger.debug("gmail.imap.authenticating", extra={"username": self.username})
            status, response = mail.login(self.username, self.password)
            if status != "OK":
                raise GmailAuthError(f"IMAP login failed: {response}")

            # Seleccionar folder
            logger.debug("gmail.imap.selecting_folder", extra={"folder": folder})
            status, response = mail.select(folder)
            if status != "OK":
                raise GmailClientError(f"Failed to select folder {folder}: {response}")

            # Buscar mensajes no leídos
            logger.debug("gmail.imap.searching", extra={"criteria": "UNSEEN"})
            status, message_ids = mail.search(None, "UNSEEN")
            if status != "OK":
                raise GmailClientError(f"Search failed: {message_ids}")

            # Procesar cada mensaje
            for num in message_ids[0].split():
                try:
                    # Fetch mensaje completo
                    status, msg_data = mail.fetch(num, "(RFC822)")
                    if status != "OK" or not msg_data or not isinstance(msg_data[0], tuple):
                        logger.warning("gmail.fetch.failed", extra={"message_id": num})
                        continue

                    # Parsear email
                    raw_bytes: bytes = msg_data[0][1]  # type: ignore
                    raw_email: Message = email.message_from_bytes(raw_bytes)

                    # Extraer campos
                    message_id = raw_email.get("Message-ID", f"no-id-{num.decode()}")
                    from_header = self._decode_header(raw_email.get("From", ""))
                    subject = self._decode_header(raw_email.get("Subject", "(sin asunto)"))
                    date_str = raw_email.get("Date", "")

                    # Extraer body (texto plano preferido)
                    body = self._extract_body(raw_email)

                    # Parsear timestamp
                    timestamp = self._parse_email_date(date_str)

                    messages.append(
                        {
                            "message_id": message_id,
                            "from": from_header,
                            "subject": subject,
                            "body": body,
                            "timestamp": timestamp,
                            "raw_email": raw_email,
                        }
                    )

                    # Marcar como leído si se solicita
                    if mark_read:
                        mail.store(num, "+FLAGS", "\\Seen")

                    logger.info(
                        "gmail.message.fetched",
                        extra={"message_id": message_id, "from": from_header, "subject": subject[:50]},
                    )

                except Exception as e:
                    logger.error("gmail.message.parse_error", extra={"message_id": num, "error": str(e)})
                    continue

            logger.info("gmail.poll.complete", extra={"count": len(messages)})
            return messages

        except imaplib.IMAP4.error as e:
            if "authentication failed" in str(e).lower():
                logger.error("gmail.auth.failed", extra={"error": str(e)})
                raise GmailAuthError(f"Authentication failed: {e}")
            else:
                logger.error("gmail.imap.error", extra={"error": str(e)})
                raise GmailClientError(f"IMAP error: {e}")
        except (OSError, ConnectionError) as e:
            logger.error("gmail.connection.failed", extra={"error": str(e)})
            raise GmailConnectionError(f"Connection failed: {e}")
        except Exception as e:
            logger.exception("gmail.poll.unexpected_error")
            raise GmailClientError(f"Unexpected error: {e}")
        finally:
            # Cerrar conexión
            if mail:
                try:
                    mail.logout()
                except Exception:
                    pass

    def send_response(
        self, to: str, subject: str, body: str, reply_to: Optional[str] = None, html: bool = False
    ) -> bool:
        """
        Send email response via SMTP.

        Args:
            to: Recipient email address
            subject: Email subject
            body: Email body (text or HTML)
            reply_to: Optional Reply-To header
            html: If True, send as HTML email

        Returns:
            True if sent successfully

        Raises:
            GmailAuthError: Authentication failed
            GmailConnectionError: Connection failed
            GmailClientError: Other SMTP errors
        """
        smtp = None

        try:
            # Crear mensaje
            logger.debug("gmail.smtp.creating_message", extra={"to": to, "subject": subject[:50]})

            msg = MIMEMultipart("alternative") if html else MIMEText(body, "plain", "utf-8")
            msg["From"] = self.username
            msg["To"] = to
            msg["Subject"] = subject
            if reply_to:
                msg["Reply-To"] = reply_to

            # Add correlation headers for traceability across systems
            cid = get_correlation_id()
            if cid:
                msg["X-Request-ID"] = cid
                msg["X-Correlation-ID"] = cid

            if html:
                # Agregar partes texto y HTML
                part_text = MIMEText(body, "plain", "utf-8")
                part_html = MIMEText(body, "html", "utf-8")
                msg.attach(part_text)
                msg.attach(part_html)

            # Conectar con timeout
            logger.debug("gmail.smtp.connecting", extra={"server": self.smtp_server})
            smtp = smtplib.SMTP_SSL(self.smtp_server, self.smtp_port, timeout=self.socket_timeout)

            # Autenticar
            logger.debug("gmail.smtp.authenticating", extra={"username": self.username})
            smtp.login(self.username, self.password)

            # Enviar
            logger.debug("gmail.smtp.sending", extra={"to": to})
            smtp.send_message(msg)

            logger.info("gmail.email.sent", extra={"to": to, "subject": subject[:50]})
            return True

        except smtplib.SMTPAuthenticationError as e:
            logger.error("gmail.smtp.auth_failed", extra={"error": str(e)})
            raise GmailAuthError(f"SMTP authentication failed: {e}")
        except (smtplib.SMTPException, OSError, ConnectionError) as e:
            logger.error("gmail.smtp.error", extra={"error": str(e)})
            raise GmailConnectionError(f"SMTP error: {e}")
        except Exception as e:
            logger.exception("gmail.send.unexpected_error")
            raise GmailClientError(f"Unexpected error: {e}")
        finally:
            # Cerrar conexión
            if smtp:
                try:
                    smtp.quit()
                except Exception:
                    pass

    def _decode_header(self, header_value: str) -> str:
        """Decode email header (handles encoding like =?UTF-8?B?...)"""
        if not header_value:
            return ""

        decoded_parts = decode_header(header_value)
        result = []
        for part, encoding in decoded_parts:
            if isinstance(part, bytes):
                result.append(part.decode(encoding or "utf-8", errors="replace"))
            else:
                result.append(str(part))
        return " ".join(result)

    def _extract_body(self, email_message: Message) -> str:
        """Extract email body (prefers text/plain over text/html)"""
        body = ""

        if email_message.is_multipart():
            # Buscar parte text/plain primero
            for part in email_message.walk():
                content_type = part.get_content_type()
                if content_type == "text/plain":
                    payload = part.get_payload(decode=True)
                    if payload and isinstance(payload, bytes):
                        charset = part.get_content_charset() or "utf-8"
                        body = payload.decode(charset, errors="replace")
                        break

            # Si no hay text/plain, usar text/html
            if not body:
                for part in email_message.walk():
                    content_type = part.get_content_type()
                    if content_type == "text/html":
                        payload = part.get_payload(decode=True)
                        if payload and isinstance(payload, bytes):
                            charset = part.get_content_charset() or "utf-8"
                            body = payload.decode(charset, errors="replace")
                            # Simplificar HTML (remover tags básicos)
                            body = self._strip_html_tags(body)
                            break
        else:
            # Mensaje simple
            payload = email_message.get_payload(decode=True)
            if payload and isinstance(payload, bytes):
                charset = email_message.get_content_charset() or "utf-8"
                body = payload.decode(charset, errors="replace")

        return body.strip()

    def _strip_html_tags(self, html: str) -> str:
        """Remove HTML tags (basic implementation)"""
        import re

        # Remover tags HTML
        text = re.sub(r"<[^>]+>", "", html)
        # Reemplazar entidades HTML comunes
        text = text.replace("&nbsp;", " ")
        text = text.replace("&lt;", "<")
        text = text.replace("&gt;", ">")
        text = text.replace("&amp;", "&")
        return text.strip()

    def _parse_email_date(self, date_str: str) -> str:
        """Parse email Date header to ISO 8601 format"""
        try:
            from email.utils import parsedate_to_datetime

            dt = parsedate_to_datetime(date_str)
            return dt.isoformat()
        except Exception:
            # Fallback a timestamp actual
            return datetime.now(timezone.utc).isoformat()
