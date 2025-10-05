# [PROMPT 2.4] app/services/gmail_client.py

import socket
from ..core.settings import settings


class GmailIMAPClient:
    def __init__(self):
        self.imap_server = "imap.gmail.com"
        self.smtp_server = "smtp.gmail.com"
        self.username = settings.gmail_username
        self.password = settings.gmail_app_password.get_secret_value()
        
        # Configurar timeout para sockets IMAP/SMTP
        # Nota: IMAPlib y SMTPlib usan socket.setdefaulttimeout()
        # pero es mejor usar timeout explícito en cada conexión
        self.socket_timeout = 30.0  # 30 segundos para operaciones IMAP/SMTP

    def poll_new_messages(self) -> list:
        # Lógica de polling con IMAPlib para buscar emails no leídos
        # y normalizarlos a UnifiedMessage
        # IMPORTANTE: Usar self.socket_timeout al crear conexión IMAP
        # Ejemplo: imaplib.IMAP4_SSL(self.imap_server, timeout=self.socket_timeout)
        return []

    def send_response(self, to: str, subject: str, body: str):
        # Lógica de envío con SMTPlib
        # IMPORTANTE: Usar self.socket_timeout al crear conexión SMTP
        # Ejemplo: smtplib.SMTP_SSL(self.smtp_server, timeout=self.socket_timeout)
        pass
