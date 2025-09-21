# [PROMPT 2.4] app/services/gmail_client.py

from ..core.settings import settings


class GmailIMAPClient:
    def __init__(self):
        self.imap_server = "imap.gmail.com"
        self.smtp_server = "smtp.gmail.com"
        self.username = settings.gmail_username
        self.password = settings.gmail_app_password.get_secret_value()

    def poll_new_messages(self) -> list:
        # Lógica de polling con IMAPlib para buscar emails no leídos
        # y normalizarlos a UnifiedMessage
        return []

    def send_response(self, to: str, subject: str, body: str):
        # Lógica de envío con SMTPlib
        pass
