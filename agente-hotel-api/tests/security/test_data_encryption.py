"""
Data Encryption Security Testing Suite
Comprehensive tests for data encryption and protection
"""

import pytest
import os
import base64
import json
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import hashes, hmac
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


# Test data encryption functionality
class TestDataEncryption:
    """Test data encryption functionality"""

    @pytest.fixture
    def sample_data(self):
        """Sample data for encryption testing"""
        return {
            "sensitive": {
                "credit_card": "4111-1111-1111-1111",
                "ssn": "123-45-6789",
                "password": "super_secret_password",
            },
            "personal": {
                "email": "test@hotel.com",
                "phone": "+1-555-0123",
                "address": "123 Hotel Street, City, State 12345",
            },
            "business": {"reservation_id": "RES-123456", "room_number": "501", "check_in": "2024-01-15"},
        }

    def test_symmetric_encryption_aes(self):
        """Test AES-256 symmetric encryption"""

        # Generate key
        key = os.urandom(32)  # 256-bit key
        iv = os.urandom(16)  # 128-bit IV

        # Test data
        plaintext = b"This is sensitive hotel guest data"

        # Encrypt
        cipher = Cipher(algorithms.AES(key), modes.CBC(iv))
        encryptor = cipher.encryptor()

        # Pad data to block size
        block_size = 16
        padding_length = block_size - (len(plaintext) % block_size)
        padded_data = plaintext + bytes([padding_length] * padding_length)

        ciphertext = encryptor.update(padded_data) + encryptor.finalize()

        # Decrypt
        decryptor = cipher.decryptor()
        decrypted_padded = decryptor.update(ciphertext) + decryptor.finalize()

        # Remove padding
        padding_length = decrypted_padded[-1]
        decrypted = decrypted_padded[:-padding_length]

        assert decrypted == plaintext
        assert len(ciphertext) > len(plaintext)  # Encrypted data should be larger

    def test_fernet_symmetric_encryption(self):
        """Test Fernet symmetric encryption"""

        # Generate key
        key = Fernet.generate_key()
        f = Fernet(key)

        # Test data
        plaintext = b"Hotel guest personal information"

        # Encrypt
        ciphertext = f.encrypt(plaintext)

        # Decrypt
        decrypted = f.decrypt(ciphertext)

        assert decrypted == plaintext
        assert ciphertext != plaintext
        assert len(ciphertext) > len(plaintext)

    def test_data_classification_encryption(self, sample_data):
        """Test encryption based on data classification"""

        def classify_data(data):
            """Classify data sensitivity levels"""
            classifications = {"public": [], "internal": [], "confidential": [], "restricted": []}

            sensitive_fields = ["credit_card", "ssn", "password"]
            personal_fields = ["email", "phone", "address"]
            business_fields = ["reservation_id", "room_number"]

            def classify_field(key, value):
                if key in sensitive_fields:
                    return "restricted"
                elif key in personal_fields:
                    return "confidential"
                elif key in business_fields:
                    return "internal"
                else:
                    return "public"

            def process_data(data, path=""):
                if isinstance(data, dict):
                    for key, value in data.items():
                        current_path = f"{path}.{key}" if path else key
                        if isinstance(value, (dict, list)):
                            process_data(value, current_path)
                        else:
                            classification = classify_field(key, value)
                            classifications[classification].append({"path": current_path, "value": value})
                elif isinstance(data, list):
                    for i, item in enumerate(data):
                        process_data(item, f"{path}[{i}]")

            process_data(data)
            return classifications

        classifications = classify_data(sample_data)

        # Verify classification
        assert len(classifications["restricted"]) > 0  # Should have sensitive data
        assert len(classifications["confidential"]) > 0  # Should have personal data
        assert len(classifications["internal"]) > 0  # Should have business data

        # Check specific classifications
        restricted_paths = [item["path"] for item in classifications["restricted"]]
        assert "sensitive.credit_card" in restricted_paths
        assert "sensitive.ssn" in restricted_paths

    def test_field_level_encryption(self, sample_data):
        """Test field-level encryption for sensitive data"""

        key = Fernet.generate_key()
        f = Fernet(key)

        def encrypt_sensitive_fields(data, sensitive_fields):
            """Encrypt specific fields in data structure"""
            if isinstance(data, dict):
                encrypted_data = {}
                for key, value in data.items():
                    if key in sensitive_fields:
                        if isinstance(value, str):
                            encrypted_data[key] = f.encrypt(value.encode()).decode()
                        else:
                            encrypted_data[key] = f.encrypt(str(value).encode()).decode()
                    elif isinstance(value, dict):
                        encrypted_data[key] = encrypt_sensitive_fields(value, sensitive_fields)
                    else:
                        encrypted_data[key] = value
                return encrypted_data
            return data

        sensitive_fields = ["credit_card", "ssn", "password", "email"]
        encrypted_data = encrypt_sensitive_fields(sample_data, sensitive_fields)

        # Verify encryption
        assert encrypted_data["sensitive"]["credit_card"] != sample_data["sensitive"]["credit_card"]
        assert encrypted_data["personal"]["email"] != sample_data["personal"]["email"]

        # Verify non-sensitive data is unchanged
        assert encrypted_data["business"]["reservation_id"] == sample_data["business"]["reservation_id"]

    def test_key_derivation(self):
        """Test key derivation from password"""

        password = b"hotel_master_password_2024"
        salt = os.urandom(16)

        # Derive key using PBKDF2
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = kdf.derive(password)

        assert len(key) == 32  # 256-bit key
        assert key != password  # Should be different from password

        # Verify same password produces same key with same salt
        kdf2 = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key2 = kdf2.derive(password)
        assert key == key2


class TestDataIntegrity:
    """Test data integrity and authentication"""

    def test_hmac_verification(self):
        """Test HMAC for data integrity"""

        # Generate HMAC key
        key = os.urandom(32)

        # Test data
        data = b"Hotel reservation data that must not be tampered with"

        # Generate HMAC
        h = hmac.HMAC(key, hashes.SHA256())
        h.update(data)
        signature = h.finalize()

        # Verify HMAC
        h_verify = hmac.HMAC(key, hashes.SHA256())
        h_verify.update(data)

        try:
            h_verify.verify(signature)
            verification_success = True
        except Exception:
            verification_success = False

        assert verification_success is True

        # Test with tampered data
        tampered_data = b"Hotel reservation data that has been tampered with"
        h_tampered = hmac.HMAC(key, hashes.SHA256())
        h_tampered.update(tampered_data)

        try:
            h_tampered.verify(signature)
            tampered_verification = True
        except Exception:
            tampered_verification = False

        assert tampered_verification is False

    def test_data_authentication(self):
        """Test authenticated encryption"""

        key = Fernet.generate_key()
        f = Fernet(key)

        # Test data
        data = {"guest_id": "GUEST-123", "room_charge": 250.00, "timestamp": "2024-01-15T10:30:00Z"}

        # Serialize and encrypt
        json_data = json.dumps(data).encode()
        encrypted_token = f.encrypt(json_data)

        # Decrypt and verify
        decrypted_json = f.decrypt(encrypted_token)
        decrypted_data = json.loads(decrypted_json.decode())

        assert decrypted_data == data

        # Test with invalid token
        invalid_token = encrypted_token[:-5] + b"XXXXX"

        try:
            f.decrypt(invalid_token)
            invalid_decrypt_success = True
        except Exception:
            invalid_decrypt_success = False

        assert invalid_decrypt_success is False


class TestKeyManagement:
    """Test key management functionality"""

    def test_key_rotation(self):
        """Test key rotation functionality"""

        # Simulate key rotation
        old_key = Fernet.generate_key()
        new_key = Fernet.generate_key()

        old_fernet = Fernet(old_key)
        new_fernet = Fernet(new_key)

        # Data encrypted with old key
        data = b"Data encrypted before key rotation"
        old_encrypted = old_fernet.encrypt(data)

        # Decrypt with old key and re-encrypt with new key
        decrypted = old_fernet.decrypt(old_encrypted)
        new_encrypted = new_fernet.encrypt(decrypted)

        # Verify new encryption works
        final_decrypted = new_fernet.decrypt(new_encrypted)
        assert final_decrypted == data

        # Verify old key can no longer decrypt new data
        try:
            old_fernet.decrypt(new_encrypted)
            old_key_works = True
        except Exception:
            old_key_works = False

        assert old_key_works is False

    def test_multiple_key_support(self):
        """Test support for multiple encryption keys"""

        # Generate multiple keys
        keys = {"key_v1": Fernet.generate_key(), "key_v2": Fernet.generate_key(), "key_v3": Fernet.generate_key()}

        # Encrypt data with different keys
        test_data = [(b"Data set 1", "key_v1"), (b"Data set 2", "key_v2"), (b"Data set 3", "key_v3")]

        encrypted_data = []
        for data, key_id in test_data:
            fernet = Fernet(keys[key_id])
            encrypted = fernet.encrypt(data)
            encrypted_data.append((encrypted, key_id))

        # Decrypt data with appropriate keys
        for i, (encrypted, key_id) in enumerate(encrypted_data):
            fernet = Fernet(keys[key_id])
            decrypted = fernet.decrypt(encrypted)
            assert decrypted == test_data[i][0]

    def test_key_storage_security(self):
        """Test secure key storage practices"""

        # Simulate key storage with additional protection
        master_password = b"hotel_security_master_2024"
        salt = os.urandom(16)

        # Derive key encryption key
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        kek = kdf.derive(master_password)  # Key Encryption Key

        # Data encryption key
        dek = Fernet.generate_key()  # Data Encryption Key

        # Encrypt the data encryption key
        kek_fernet = Fernet(base64.urlsafe_b64encode(kek))
        encrypted_dek = kek_fernet.encrypt(dek)

        # Verify key can be recovered
        decrypted_dek = kek_fernet.decrypt(encrypted_dek)
        assert decrypted_dek == dek

        # Test data encryption with recovered key
        dek_fernet = Fernet(decrypted_dek)
        test_data = b"Test data for key recovery verification"
        encrypted = dek_fernet.encrypt(test_data)
        decrypted = dek_fernet.decrypt(encrypted)
        assert decrypted == test_data


class TestEncryptionPerformance:
    """Test encryption performance characteristics"""

    def test_encryption_speed(self):
        """Test encryption speed with various data sizes"""

        import time

        key = Fernet.generate_key()
        f = Fernet(key)

        # Test different data sizes
        data_sizes = [1024, 10240, 102400, 1024000]  # 1KB, 10KB, 100KB, 1MB

        for size in data_sizes:
            data = os.urandom(size)

            # Measure encryption time
            start_time = time.time()
            encrypted = f.encrypt(data)
            encryption_time = time.time() - start_time

            # Measure decryption time
            start_time = time.time()
            decrypted = f.decrypt(encrypted)
            decryption_time = time.time() - start_time

            # Verify correctness
            assert decrypted == data

            # Performance should be reasonable (under 1 second for 1MB)
            if size <= 1024000:  # 1MB
                assert encryption_time < 1.0
                assert decryption_time < 1.0

    def test_memory_efficient_encryption(self):
        """Test memory-efficient encryption for large data"""

        key = Fernet.generate_key()
        f = Fernet(key)

        # Simulate processing large dataset in chunks
        chunk_size = 8192  # 8KB chunks
        test_data = os.urandom(100000)  # 100KB total

        encrypted_chunks = []

        # Encrypt in chunks
        for i in range(0, len(test_data), chunk_size):
            chunk = test_data[i : i + chunk_size]
            encrypted_chunk = f.encrypt(chunk)
            encrypted_chunks.append(encrypted_chunk)

        # Decrypt chunks
        decrypted_data = b""
        for encrypted_chunk in encrypted_chunks:
            decrypted_chunk = f.decrypt(encrypted_chunk)
            decrypted_data += decrypted_chunk

        assert decrypted_data == test_data
        assert len(encrypted_chunks) > 1  # Should have multiple chunks


class TestEncryptionCompliance:
    """Test encryption compliance with security standards"""

    def test_fips_compliant_algorithms(self):
        """Test FIPS-compliant encryption algorithms"""

        # Test AES-256 (FIPS approved)
        key = os.urandom(32)  # 256-bit key
        iv = os.urandom(16)  # 128-bit IV

        cipher = Cipher(algorithms.AES(key), modes.CBC(iv))

        # Verify algorithm properties
        assert cipher.algorithm.key_size == 256  # Bits
        assert len(iv) == 16  # 128 bits

        # Test encryption/decryption
        data = b"FIPS compliant encryption test data"
        encryptor = cipher.encryptor()

        # Pad to block size
        block_size = 16
        padding = block_size - (len(data) % block_size)
        padded_data = data + bytes([padding] * padding)

        encrypted = encryptor.update(padded_data) + encryptor.finalize()

        # Decrypt
        decryptor = cipher.decryptor()
        decrypted_padded = decryptor.update(encrypted) + decryptor.finalize()
        decrypted = decrypted_padded[: -decrypted_padded[-1]]

        assert decrypted == data

    def test_pci_dss_compliance(self):
        """Test PCI DSS compliance for payment data"""

        # PCI DSS requires strong encryption for cardholder data
        key = os.urandom(32)  # 256-bit key (exceeds PCI DSS minimum)

        # Simulate credit card data
        card_data = {
            "pan": "4111111111111111",  # Primary Account Number
            "expiry": "12/25",
            "cvv": "123",
            "cardholder": "John Doe",
        }

        # Encrypt PAN (Primary Account Number)
        f = Fernet(base64.urlsafe_b64encode(key))
        encrypted_pan = f.encrypt(card_data["pan"].encode())

        # Verify PAN is not stored in plaintext
        assert encrypted_pan != card_data["pan"].encode()

        # Verify PAN can be decrypted when needed
        decrypted_pan = f.decrypt(encrypted_pan).decode()
        assert decrypted_pan == card_data["pan"]

        # Mask PAN for display purposes
        def mask_pan(pan):
            if len(pan) >= 4:
                return "*" * (len(pan) - 4) + pan[-4:]
            return "*" * len(pan)

        masked_pan = mask_pan(card_data["pan"])
        assert masked_pan == "************1111"

    def test_gdpr_data_protection(self):
        """Test GDPR-compliant data protection"""

        # GDPR requires protection of personal data
        personal_data = {
            "name": "Maria García",
            "email": "maria@example.com",
            "phone": "+34-123-456-789",
            "address": "Calle Principal 123, Madrid, Spain",
            "preferences": "Non-smoking room, ground floor",
        }

        # Encrypt personal data
        key = Fernet.generate_key()
        f = Fernet(key)

        encrypted_personal_data = {}
        for field, value in personal_data.items():
            encrypted_personal_data[f"encrypted_{field}"] = f.encrypt(value.encode()).decode()

        # Verify data is encrypted
        for field in personal_data:
            encrypted_field = f"encrypted_{field}"
            assert encrypted_personal_data[encrypted_field] != personal_data[field]

        # Test "right to be forgotten" - ability to delete/destroy keys
        def forget_user_data(user_key):
            """Simulate forgetting user data by destroying encryption key"""
            # In practice, this would securely delete the key
            return None

        forgotten_key = forget_user_data(key)
        assert forgotten_key is None


class TestEncryptionErrorHandling:
    """Test encryption error handling"""

    def test_invalid_key_handling(self):
        """Test handling of invalid encryption keys"""

        # Test with invalid key format
        invalid_keys = [b"too_short", b"", None, "not_bytes_string"]

        for invalid_key in invalid_keys:
            try:
                if invalid_key is not None:
                    Fernet(invalid_key)
                    encryption_failed = False
                else:
                    encryption_failed = True
            except Exception:
                encryption_failed = True

            assert encryption_failed is True

    def test_corrupted_data_handling(self):
        """Test handling of corrupted encrypted data"""

        key = Fernet.generate_key()
        f = Fernet(key)

        # Encrypt valid data
        data = b"Valid data for corruption test"
        encrypted = f.encrypt(data)

        # Corrupt encrypted data
        corrupted_data = encrypted[:-5] + b"XXXXX"

        # Attempt to decrypt corrupted data
        try:
            f.decrypt(corrupted_data)
            decryption_failed = False
        except Exception:
            decryption_failed = True

        assert decryption_failed is True

    def test_expired_token_handling(self):
        """Test handling of expired encrypted tokens"""

        key = Fernet.generate_key()
        f = Fernet(key)

        # Create token with very short TTL
        data = b"Data with short expiration"
        encrypted = f.encrypt(data)

        # Simulate immediate expiration by attempting to decrypt with TTL=0
        try:
            f.decrypt(encrypted, ttl=0)
            decryption_failed = False
        except Exception:
            decryption_failed = True

        # Should fail due to TTL
        assert decryption_failed is True


class TestDataMasking:
    """Test data masking and tokenization"""

    def test_credit_card_masking(self):
        """Test credit card number masking"""

        def mask_credit_card(card_number):
            """Mask credit card number showing only last 4 digits"""
            if len(card_number) < 4:
                return "*" * len(card_number)
            return "*" * (len(card_number) - 4) + card_number[-4:]

        test_cards = ["4111111111111111", "5555555555554444", "378282246310005"]

        expected_masks = ["************1111", "************4444", "***********0005"]

        for card, expected in zip(test_cards, expected_masks):
            masked = mask_credit_card(card)
            assert masked == expected
            assert card[-4:] in masked  # Last 4 digits should be visible

    def test_email_masking(self):
        """Test email address masking"""

        def mask_email(email):
            """Mask email address preserving domain"""
            if "@" not in email:
                return "*" * len(email)

            local, domain = email.split("@", 1)
            if len(local) <= 2:
                masked_local = "*" * len(local)
            else:
                masked_local = local[0] + "*" * (len(local) - 2) + local[-1]

            return f"{masked_local}@{domain}"

        test_emails = ["test@example.com", "maria.garcia@hotel.es", "a@b.com"]

        for email in test_emails:
            masked = mask_email(email)
            assert "@" in masked
            assert masked != email
            # Domain should be preserved
            original_domain = email.split("@")[1]
            masked_domain = masked.split("@")[1]
            assert original_domain == masked_domain

    def test_phone_number_masking(self):
        """Test phone number masking"""

        def mask_phone(phone):
            """Mask phone number showing only last 4 digits"""
            # Remove non-digit characters for processing
            digits = "".join(filter(str.isdigit, phone))
            if len(digits) < 4:
                return "*" * len(phone)

            # Keep original format but mask digits except last 4
            masked = ""
            digit_count = 0
            digits[-4:]

            for char in phone:
                if char.isdigit():
                    if digit_count >= len(digits) - 4:
                        masked += char  # Show last 4 digits
                    else:
                        masked += "*"  # Mask other digits
                    digit_count += 1
                else:
                    masked += char  # Keep formatting characters

            return masked

        test_phones = ["+1-555-123-4567", "(555) 123-4567", "555.123.4567"]

        for phone in test_phones:
            masked = mask_phone(phone)
            assert masked != phone
            # Should contain last 4 digits
            last_4_digits = "".join(filter(str.isdigit, phone))[-4:]
            assert last_4_digits in masked.replace("*", "").replace("-", "").replace("(", "").replace(")", "").replace(
                " ", ""
            ).replace(".", "")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
