# [PROMPT 3.2] app/core/encryption.py

from cryptography.fernet import Fernet
from .settings import settings


class EncryptionService:
    def __init__(self):
        # En producción, la key debe ser gestionada de forma segura (ej. Vault)
        key = settings.secret_key.get_secret_value().encode()  # Reutilizando secret_key por simplicidad
        self.cipher = Fernet(key)

    def encrypt_sensitive_data(self, data: str) -> str:
        return self.cipher.encrypt(data.encode()).decode()

    def decrypt_sensitive_data(self, encrypted_data: str) -> str:
        return self.cipher.decrypt(encrypted_data.encode()).decode()


encryption_service = EncryptionService()
