"""
Data Encryption and Protection Service
Advanced encryption for sensitive data protection
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional, Union, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import secrets
import hashlib
import hmac
from base64 import b64encode, b64decode
import json

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend

from prometheus_client import Counter, Histogram

logger = logging.getLogger(__name__)

# Prometheus metrics
encryption_operations_total = Counter(
    "encryption_operations_total",
    "Total encryption operations",
    ["operation", "algorithm", "status"]
)

encryption_duration_seconds = Histogram(
    "encryption_duration_seconds",
    "Encryption operation duration",
    ["operation", "algorithm"]
)

class EncryptionAlgorithm(Enum):
    """Supported encryption algorithms"""
    AES_256_GCM = "aes_256_gcm"
    FERNET = "fernet"
    RSA_2048 = "rsa_2048"
    RSA_4096 = "rsa_4096"
    CHACHA20_POLY1305 = "chacha20_poly1305"

class DataClassification(Enum):
    """Data classification levels"""
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"
    TOP_SECRET = "top_secret"

@dataclass
class EncryptedData:
    """Encrypted data container"""
    encrypted_data: bytes
    algorithm: EncryptionAlgorithm
    key_id: str
    nonce: Optional[bytes] = None
    tag: Optional[bytes] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        return {
            "encrypted_data": b64encode(self.encrypted_data).decode(),
            "algorithm": self.algorithm.value,
            "key_id": self.key_id,
            "nonce": b64encode(self.nonce).decode() if self.nonce else None,
            "tag": b64encode(self.tag).decode() if self.tag else None,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'EncryptedData':
        """Create from dictionary"""
        return cls(
            encrypted_data=b64decode(data["encrypted_data"]),
            algorithm=EncryptionAlgorithm(data["algorithm"]),
            key_id=data["key_id"],
            nonce=b64decode(data["nonce"]) if data.get("nonce") else None,
            tag=b64decode(data["tag"]) if data.get("tag") else None,
            metadata=data.get("metadata", {}),
            created_at=datetime.fromisoformat(data["created_at"])
        )

@dataclass
class EncryptionKey:
    """Encryption key metadata"""
    key_id: str
    algorithm: EncryptionAlgorithm
    key_data: bytes
    classification: DataClassification
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: Optional[datetime] = None
    is_active: bool = True
    rotation_count: int = 0

class DataEncryptionService:
    """Advanced data encryption and protection service"""
    
    def __init__(self):
        # Encryption keys storage
        self.encryption_keys: Dict[str, EncryptionKey] = {}
        self.master_key: Optional[bytes] = None
        
        # Key rotation settings
        self.key_rotation_interval_days = 90
        self.max_key_age_days = 365
        
        # Algorithm preferences by classification
        self.algorithm_preferences = {
            DataClassification.PUBLIC: EncryptionAlgorithm.FERNET,
            DataClassification.INTERNAL: EncryptionAlgorithm.AES_256_GCM,
            DataClassification.CONFIDENTIAL: EncryptionAlgorithm.AES_256_GCM,
            DataClassification.RESTRICTED: EncryptionAlgorithm.AES_256_GCM,
            DataClassification.TOP_SECRET: EncryptionAlgorithm.RSA_4096
        }
        
        logger.info("Data Encryption Service initialized")
    
    async def initialize(self):
        """Initialize encryption service"""
        try:
            # Generate or load master key
            self.master_key = self._generate_master_key()
            
            # Initialize default encryption keys
            await self._initialize_default_keys()
            
            logger.info("Data Encryption Service initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize encryption service: {e}")
            raise
    
    def _generate_master_key(self) -> bytes:
        """Generate master encryption key"""
        # In production, this should be loaded from secure key management
        return secrets.token_bytes(32)  # 256-bit key
    
    async def _initialize_default_keys(self):
        """Initialize default encryption keys for each classification"""
        
        for classification in DataClassification:
            algorithm = self.algorithm_preferences[classification]
            key_id = f"default_{classification.value}_{datetime.now().strftime('%Y%m%d')}"
            
            key_data = await self._generate_key(algorithm)
            
            encryption_key = EncryptionKey(
                key_id=key_id,
                algorithm=algorithm,
                key_data=key_data,
                classification=classification
            )
            
            self.encryption_keys[key_id] = encryption_key
            
        logger.info(f"Initialized {len(self.encryption_keys)} default encryption keys")
    
    async def _generate_key(self, algorithm: EncryptionAlgorithm) -> bytes:
        """Generate encryption key for specific algorithm"""
        
        if algorithm == EncryptionAlgorithm.AES_256_GCM:
            return secrets.token_bytes(32)  # 256-bit key
        elif algorithm == EncryptionAlgorithm.FERNET:
            return Fernet.generate_key()
        elif algorithm == EncryptionAlgorithm.CHACHA20_POLY1305:
            return secrets.token_bytes(32)  # 256-bit key
        elif algorithm in [EncryptionAlgorithm.RSA_2048, EncryptionAlgorithm.RSA_4096]:
            # Generate RSA key pair
            key_size = 2048 if algorithm == EncryptionAlgorithm.RSA_2048 else 4096
            private_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=key_size,
                backend=default_backend()
            )
            
            # Return private key in PEM format
            return private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            )
        else:
            raise ValueError(f"Unsupported algorithm: {algorithm}")
    
    async def encrypt_data(self, data: Union[str, bytes], 
                         classification: DataClassification,
                         algorithm: Optional[EncryptionAlgorithm] = None,
                         key_id: Optional[str] = None) -> EncryptedData:
        """Encrypt data with specified or default algorithm"""
        
        start_time = asyncio.get_event_loop().time()
        
        try:
            # Convert string to bytes if needed
            if isinstance(data, str):
                data = data.encode('utf-8')
            
            # Determine algorithm and key
            if not algorithm:
                algorithm = self.algorithm_preferences[classification]
            
            if not key_id:
                key_id = self._get_default_key_id(classification, algorithm)
            
            encryption_key = self.encryption_keys.get(key_id)
            if not encryption_key:
                raise ValueError(f"Encryption key not found: {key_id}")
            
            # Perform encryption based on algorithm
            if algorithm == EncryptionAlgorithm.AES_256_GCM:
                encrypted_data = await self._encrypt_aes_gcm(data, encryption_key.key_data)
            elif algorithm == EncryptionAlgorithm.FERNET:
                encrypted_data = await self._encrypt_fernet(data, encryption_key.key_data)
            elif algorithm == EncryptionAlgorithm.CHACHA20_POLY1305:
                encrypted_data = await self._encrypt_chacha20(data, encryption_key.key_data)
            elif algorithm in [EncryptionAlgorithm.RSA_2048, EncryptionAlgorithm.RSA_4096]:
                encrypted_data = await self._encrypt_rsa(data, encryption_key.key_data)
            else:
                raise ValueError(f"Unsupported algorithm: {algorithm}")
            
            # Update metrics
            duration = asyncio.get_event_loop().time() - start_time
            encryption_duration_seconds.labels(
                operation="encrypt",
                algorithm=algorithm.value
            ).observe(duration)
            
            encryption_operations_total.labels(
                operation="encrypt",
                algorithm=algorithm.value,
                status="success"
            ).inc()
            
            logger.debug(f"Data encrypted successfully with {algorithm.value}")
            return encrypted_data
            
        except Exception as e:
            encryption_operations_total.labels(
                operation="encrypt",
                algorithm=algorithm.value if algorithm else "unknown",
                status="error"
            ).inc()
            
            logger.error(f"Encryption failed: {e}")
            raise
    
    async def decrypt_data(self, encrypted_data: EncryptedData) -> bytes:
        """Decrypt encrypted data"""
        
        start_time = asyncio.get_event_loop().time()
        
        try:
            encryption_key = self.encryption_keys.get(encrypted_data.key_id)
            if not encryption_key:
                raise ValueError(f"Encryption key not found: {encrypted_data.key_id}")
            
            # Perform decryption based on algorithm
            if encrypted_data.algorithm == EncryptionAlgorithm.AES_256_GCM:
                data = await self._decrypt_aes_gcm(encrypted_data, encryption_key.key_data)
            elif encrypted_data.algorithm == EncryptionAlgorithm.FERNET:
                data = await self._decrypt_fernet(encrypted_data, encryption_key.key_data)
            elif encrypted_data.algorithm == EncryptionAlgorithm.CHACHA20_POLY1305:
                data = await self._decrypt_chacha20(encrypted_data, encryption_key.key_data)
            elif encrypted_data.algorithm in [EncryptionAlgorithm.RSA_2048, EncryptionAlgorithm.RSA_4096]:
                data = await self._decrypt_rsa(encrypted_data, encryption_key.key_data)
            else:
                raise ValueError(f"Unsupported algorithm: {encrypted_data.algorithm}")
            
            # Update metrics
            duration = asyncio.get_event_loop().time() - start_time
            encryption_duration_seconds.labels(
                operation="decrypt",
                algorithm=encrypted_data.algorithm.value
            ).observe(duration)
            
            encryption_operations_total.labels(
                operation="decrypt",
                algorithm=encrypted_data.algorithm.value,
                status="success"
            ).inc()
            
            logger.debug(f"Data decrypted successfully with {encrypted_data.algorithm.value}")
            return data
            
        except Exception as e:
            encryption_operations_total.labels(
                operation="decrypt",
                algorithm=encrypted_data.algorithm.value,
                status="error"
            ).inc()
            
            logger.error(f"Decryption failed: {e}")
            raise
    
    async def _encrypt_aes_gcm(self, data: bytes, key: bytes) -> EncryptedData:
        """Encrypt with AES-256-GCM"""
        
        nonce = secrets.token_bytes(12)  # 96-bit nonce for GCM
        cipher = Cipher(algorithms.AES(key), modes.GCM(nonce), backend=default_backend())
        encryptor = cipher.encryptor()
        
        ciphertext = encryptor.update(data) + encryptor.finalize()
        
        return EncryptedData(
            encrypted_data=ciphertext,
            algorithm=EncryptionAlgorithm.AES_256_GCM,
            key_id="", # Will be set by caller
            nonce=nonce,
            tag=encryptor.tag
        )
    
    async def _decrypt_aes_gcm(self, encrypted_data: EncryptedData, key: bytes) -> bytes:
        """Decrypt with AES-256-GCM"""
        
        cipher = Cipher(
            algorithms.AES(key), 
            modes.GCM(encrypted_data.nonce, encrypted_data.tag), 
            backend=default_backend()
        )
        decryptor = cipher.decryptor()
        
        return decryptor.update(encrypted_data.encrypted_data) + decryptor.finalize()
    
    async def _encrypt_fernet(self, data: bytes, key: bytes) -> EncryptedData:
        """Encrypt with Fernet (AES-128 + HMAC)"""
        
        f = Fernet(key)
        ciphertext = f.encrypt(data)
        
        return EncryptedData(
            encrypted_data=ciphertext,
            algorithm=EncryptionAlgorithm.FERNET,
            key_id="" # Will be set by caller
        )
    
    async def _decrypt_fernet(self, encrypted_data: EncryptedData, key: bytes) -> bytes:
        """Decrypt with Fernet"""
        
        f = Fernet(key)
        return f.decrypt(encrypted_data.encrypted_data)
    
    async def _encrypt_chacha20(self, data: bytes, key: bytes) -> EncryptedData:
        """Encrypt with ChaCha20-Poly1305"""
        
        nonce = secrets.token_bytes(12)  # 96-bit nonce
        cipher = Cipher(algorithms.ChaCha20(key, nonce), None, backend=default_backend())
        encryptor = cipher.encryptor()
        
        ciphertext = encryptor.update(data) + encryptor.finalize()
        
        return EncryptedData(
            encrypted_data=ciphertext,
            algorithm=EncryptionAlgorithm.CHACHA20_POLY1305,
            key_id="", # Will be set by caller
            nonce=nonce
        )
    
    async def _decrypt_chacha20(self, encrypted_data: EncryptedData, key: bytes) -> bytes:
        """Decrypt with ChaCha20-Poly1305"""
        
        cipher = Cipher(
            algorithms.ChaCha20(key, encrypted_data.nonce), 
            None, 
            backend=default_backend()
        )
        decryptor = cipher.decryptor()
        
        return decryptor.update(encrypted_data.encrypted_data) + decryptor.finalize()
    
    async def _encrypt_rsa(self, data: bytes, private_key_pem: bytes) -> EncryptedData:
        """Encrypt with RSA (using public key from private key)"""
        
        # Load private key and extract public key
        private_key = serialization.load_pem_private_key(
            private_key_pem, 
            password=None, 
            backend=default_backend()
        )
        public_key = private_key.public_key()
        
        # RSA encryption (for small data only)
        if len(data) > 190:  # RSA-2048 can encrypt max ~190 bytes
            raise ValueError("Data too large for RSA encryption")
        
        ciphertext = public_key.encrypt(
            data,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
        
        return EncryptedData(
            encrypted_data=ciphertext,
            algorithm=EncryptionAlgorithm.RSA_2048,  # Will be updated by caller
            key_id="" # Will be set by caller
        )
    
    async def _decrypt_rsa(self, encrypted_data: EncryptedData, private_key_pem: bytes) -> bytes:
        """Decrypt with RSA (using private key)"""
        
        private_key = serialization.load_pem_private_key(
            private_key_pem, 
            password=None, 
            backend=default_backend()
        )
        
        plaintext = private_key.decrypt(
            encrypted_data.encrypted_data,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
        
        return plaintext
    
    def _get_default_key_id(self, classification: DataClassification, 
                          algorithm: EncryptionAlgorithm) -> str:
        """Get default key ID for classification and algorithm"""
        
        for key_id, key in self.encryption_keys.items():
            if key.classification == classification and key.algorithm == algorithm and key.is_active:
                return key_id
        
        raise ValueError(f"No active key found for {classification.value} with {algorithm.value}")
    
    async def create_encryption_key(self, classification: DataClassification,
                                  algorithm: Optional[EncryptionAlgorithm] = None) -> str:
        """Create new encryption key"""
        
        if not algorithm:
            algorithm = self.algorithm_preferences[classification]
        
        key_id = f"{classification.value}_{algorithm.value}_{secrets.token_hex(8)}"
        key_data = await self._generate_key(algorithm)
        
        encryption_key = EncryptionKey(
            key_id=key_id,
            algorithm=algorithm,
            key_data=key_data,
            classification=classification
        )
        
        self.encryption_keys[key_id] = encryption_key
        
        logger.info(f"Created new encryption key: {key_id}")
        return key_id
    
    async def rotate_key(self, key_id: str) -> str:
        """Rotate encryption key"""
        
        old_key = self.encryption_keys.get(key_id)
        if not old_key:
            raise ValueError(f"Key not found: {key_id}")
        
        # Create new key with same properties
        new_key_id = await self.create_encryption_key(
            old_key.classification, 
            old_key.algorithm
        )
        
        # Deactivate old key
        old_key.is_active = False
        old_key.rotation_count += 1
        
        logger.info(f"Rotated key {key_id} to {new_key_id}")
        return new_key_id
    
    def hash_password(self, password: str, salt: Optional[bytes] = None) -> Tuple[bytes, bytes]:
        """Hash password using PBKDF2"""
        
        if not salt:
            salt = secrets.token_bytes(32)
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
            backend=default_backend()
        )
        
        key = kdf.derive(password.encode('utf-8'))
        return key, salt
    
    def verify_password(self, password: str, hashed: bytes, salt: bytes) -> bool:
        """Verify password against hash"""
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
            backend=default_backend()
        )
        
        try:
            kdf.verify(password.encode('utf-8'), hashed)
            return True
        except:
            return False
    
    def generate_secure_token(self, length: int = 32) -> str:
        """Generate cryptographically secure token"""
        return secrets.token_urlsafe(length)
    
    def compute_hmac(self, data: bytes, key: bytes) -> bytes:
        """Compute HMAC-SHA256"""
        return hmac.new(key, data, hashlib.sha256).digest()
    
    def verify_hmac(self, data: bytes, key: bytes, signature: bytes) -> bool:
        """Verify HMAC signature"""
        expected = self.compute_hmac(data, key)
        return hmac.compare_digest(expected, signature)
    
    async def encrypt_pii_data(self, pii_data: Dict[str, Any]) -> Dict[str, Any]:
        """Encrypt personally identifiable information"""
        
        encrypted_pii = {}
        
        # Fields that should be encrypted
        pii_fields = [
            "email", "phone", "ssn", "passport_number", 
            "credit_card", "address", "date_of_birth"
        ]
        
        for field, value in pii_data.items():
            if field in pii_fields and value:
                encrypted_data = await self.encrypt_data(
                    str(value), 
                    DataClassification.RESTRICTED
                )
                encrypted_pii[field] = encrypted_data.to_dict()
            else:
                encrypted_pii[field] = value
        
        return encrypted_pii
    
    async def decrypt_pii_data(self, encrypted_pii: Dict[str, Any]) -> Dict[str, Any]:
        """Decrypt personally identifiable information"""
        
        decrypted_pii = {}
        
        for field, value in encrypted_pii.items():
            if isinstance(value, dict) and "encrypted_data" in value:
                encrypted_data = EncryptedData.from_dict(value)
                decrypted_bytes = await self.decrypt_data(encrypted_data)
                decrypted_pii[field] = decrypted_bytes.decode('utf-8')
            else:
                decrypted_pii[field] = value
        
        return decrypted_pii
    
    async def get_encryption_status(self) -> Dict[str, Any]:
        """Get encryption service status"""
        
        active_keys = sum(1 for key in self.encryption_keys.values() if key.is_active)
        
        keys_by_classification = {}
        for key in self.encryption_keys.values():
            if key.is_active:
                classification = key.classification.value
                if classification not in keys_by_classification:
                    keys_by_classification[classification] = 0
                keys_by_classification[classification] += 1
        
        return {
            "total_keys": len(self.encryption_keys),
            "active_keys": active_keys,
            "keys_by_classification": keys_by_classification,
            "supported_algorithms": [alg.value for alg in EncryptionAlgorithm],
            "master_key_present": self.master_key is not None
        }

# Global instance
_encryption_service = None

async def get_encryption_service() -> DataEncryptionService:
    """Get global encryption service instance"""
    global _encryption_service
    if _encryption_service is None:
        _encryption_service = DataEncryptionService()
        await _encryption_service.initialize()
    return _encryption_service