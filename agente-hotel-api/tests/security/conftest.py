"""
Security Test Configuration and Fixtures
Central configuration for all security tests
"""

import pytest
import pytest_asyncio
from unittest.mock import Mock, AsyncMock, MagicMock
import tempfile
import os
import json
import redis
from datetime import datetime, timedelta
import secrets

# Global test configuration
class SecurityTestConfig:
    """Configuration for security tests"""
    
    # Test database settings
    TEST_DATABASE_URL = "sqlite:///./test_security.db"
    TEST_REDIS_URL = "redis://localhost:6379/15"  # Use DB 15 for tests
    
    # Test user credentials
    TEST_USERS = {
        "admin": {
            "user_id": "admin_123",
            "username": "admin",
            "email": "admin@hotel.com",
            "password_hash": "$2b$12$hashed_admin_password",
            "roles": ["admin", "hotel_manager"],
            "is_active": True,
            "mfa_enabled": True
        },
        "manager": {
            "user_id": "manager_123", 
            "username": "manager",
            "email": "manager@hotel.com",
            "password_hash": "$2b$12$hashed_manager_password",
            "roles": ["hotel_manager"],
            "is_active": True,
            "mfa_enabled": False
        },
        "guest": {
            "user_id": "guest_123",
            "username": "guest",
            "email": "guest@hotel.com",
            "password_hash": "$2b$12$hashed_guest_password",
            "roles": ["guest"],
            "is_active": True,
            "mfa_enabled": False
        },
        "locked_user": {
            "user_id": "locked_123",
            "username": "locked_user",
            "email": "locked@hotel.com",
            "password_hash": "$2b$12$hashed_locked_password",
            "roles": ["guest"],
            "is_active": False,
            "mfa_enabled": False
        }
    }
    
    # Test JWT settings
    JWT_SECRET_KEY = "test_jwt_secret_key_for_security_tests_only"
    JWT_ALGORITHM = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES = 30
    JWT_REFRESH_TOKEN_EXPIRE_DAYS = 7
    
    # Rate limiting settings
    RATE_LIMIT_REQUESTS_PER_MINUTE = 60
    RATE_LIMIT_BURST_MULTIPLIER = 2
    
    # Security policies
    MAX_LOGIN_ATTEMPTS = 5
    ACCOUNT_LOCKOUT_DURATION_MINUTES = 30
    PASSWORD_MIN_LENGTH = 8
    PASSWORD_REQUIRE_UPPERCASE = True
    PASSWORD_REQUIRE_LOWERCASE = True
    PASSWORD_REQUIRE_NUMBERS = True
    PASSWORD_REQUIRE_SPECIAL_CHARS = True
    
    # Encryption settings
    ENCRYPTION_KEY = b"test_encryption_key_32_bytes_long"  # 32 bytes for Fernet
    
    # Audit log settings
    AUDIT_LOG_RETENTION_DAYS = 90

@pytest.fixture(scope="session")
def security_config():
    """Provide security test configuration"""
    return SecurityTestConfig()

@pytest.fixture(scope="function")
def mock_redis():
    """Mock Redis client for testing"""
    redis_mock = MagicMock()
    
    # Mock Redis data storage
    redis_data = {}
    
    def mock_get(key):
        return redis_data.get(key)
    
    def mock_set(key, value, ex=None):
        redis_data[key] = value
        return True
    
    def mock_delete(key):
        if key in redis_data:
            del redis_data[key]
            return 1
        return 0
    
    def mock_exists(key):
        return 1 if key in redis_data else 0
    
    def mock_incr(key):
        current = int(redis_data.get(key, 0))
        redis_data[key] = str(current + 1)
        return current + 1
    
    def mock_expire(key, seconds):
        # In real Redis, this would set expiration
        return True
    
    def mock_keys(pattern):
        if pattern.endswith("*"):
            prefix = pattern[:-1]
            return [key for key in redis_data.keys() if key.startswith(prefix)]
        return [key for key in redis_data.keys() if key == pattern]
    
    redis_mock.get = mock_get
    redis_mock.set = mock_set
    redis_mock.delete = mock_delete
    redis_mock.exists = mock_exists
    redis_mock.incr = mock_incr
    redis_mock.expire = mock_expire
    redis_mock.keys = mock_keys
    
    return redis_mock

@pytest.fixture(scope="function")
def mock_database():
    """Mock database for testing"""
    
    class MockDatabase:
        def __init__(self):
            self.users = SecurityTestConfig.TEST_USERS.copy()
            self.sessions = {}
            self.audit_logs = []
            self.rate_limit_data = {}
            
        async def get_user_by_username(self, username):
            return self.users.get(username)
        
        async def get_user_by_id(self, user_id):
            for user in self.users.values():
                if user["user_id"] == user_id:
                    return user
            return None
        
        async def create_user(self, user_data):
            username = user_data["username"]
            self.users[username] = user_data
            return user_data
        
        async def update_user(self, username, updates):
            if username in self.users:
                self.users[username].update(updates)
                return self.users[username]
            return None
        
        async def delete_user(self, username):
            if username in self.users:
                del self.users[username]
                return True
            return False
        
        async def create_session(self, session_data):
            session_id = session_data["session_id"]
            self.sessions[session_id] = session_data
            return session_data
        
        async def get_session(self, session_id):
            return self.sessions.get(session_id)
        
        async def delete_session(self, session_id):
            if session_id in self.sessions:
                del self.sessions[session_id]
                return True
            return False
        
        async def log_audit_event(self, event_data):
            event_data["id"] = len(self.audit_logs) + 1
            event_data["timestamp"] = datetime.utcnow().isoformat()
            self.audit_logs.append(event_data)
            return event_data
        
        async def get_audit_logs(self, limit=100, offset=0):
            return self.audit_logs[offset:offset + limit]
    
    return MockDatabase()

@pytest.fixture(scope="function")
def mock_jwt_service():
    """Mock JWT service for testing"""
    
    class MockJWTService:
        def __init__(self):
            self.secret_key = SecurityTestConfig.JWT_SECRET_KEY
            self.algorithm = SecurityTestConfig.JWT_ALGORITHM
            self.tokens = {}  # Store tokens for validation
        
        def create_access_token(self, data: dict, expires_delta=None):
            token = f"access_token_{secrets.token_urlsafe(16)}"
            self.tokens[token] = {
                "type": "access",
                "data": data,
                "expires_at": datetime.utcnow() + (expires_delta or timedelta(minutes=30))
            }
            return token
        
        def create_refresh_token(self, data: dict):
            token = f"refresh_token_{secrets.token_urlsafe(16)}"
            self.tokens[token] = {
                "type": "refresh",
                "data": data,
                "expires_at": datetime.utcnow() + timedelta(days=7)
            }
            return token
        
        def verify_token(self, token: str):
            if token not in self.tokens:
                raise Exception("Token not found")
            
            token_data = self.tokens[token]
            if datetime.utcnow() > token_data["expires_at"]:
                raise Exception("Token expired")
            
            return token_data["data"]
        
        def revoke_token(self, token: str):
            if token in self.tokens:
                del self.tokens[token]
                return True
            return False
    
    return MockJWTService()

@pytest.fixture(scope="function")
def mock_encryption_service():
    """Mock encryption service for testing"""
    
    class MockEncryptionService:
        def __init__(self):
            self.encrypted_data = {}
            self.key_counter = 0
        
        def encrypt(self, data: str, key_id=None):
            """Simulate encryption by base64 encoding with a prefix"""
            import base64
            encrypted = base64.b64encode(data.encode()).decode()
            encrypted_key = f"enc_{self.key_counter}_{encrypted}"
            self.key_counter += 1
            
            if key_id:
                self.encrypted_data[key_id] = encrypted_key
            
            return encrypted_key
        
        def decrypt(self, encrypted_data: str, key_id=None):
            """Simulate decryption"""
            import base64
            
            if encrypted_data.startswith("enc_"):
                # Extract the base64 part
                parts = encrypted_data.split("_", 2)
                if len(parts) >= 3:
                    encoded_data = parts[2]
                    try:
                        return base64.b64decode(encoded_data).decode()
                    except:
                        raise Exception("Decryption failed")
            
            raise Exception("Invalid encrypted data format")
        
        def hash_password(self, password: str):
            """Mock password hashing"""
            import hashlib
            return f"$2b$12${hashlib.sha256(password.encode()).hexdigest()}"
        
        def verify_password(self, password: str, hashed: str):
            """Mock password verification"""
            return self.hash_password(password) == hashed
    
    return MockEncryptionService()

@pytest.fixture(scope="function")
def mock_audit_logger():
    """Mock audit logger for testing"""
    
    class MockAuditLogger:
        def __init__(self):
            self.logs = []
        
        async def log_event(self, event_type: str, user_id: str = None, 
                          details: dict = None, ip_address: str = None):
            log_entry = {
                "id": len(self.logs) + 1,
                "timestamp": datetime.utcnow().isoformat(),
                "event_type": event_type,
                "user_id": user_id,
                "details": details or {},
                "ip_address": ip_address or "127.0.0.1"
            }
            self.logs.append(log_entry)
            return log_entry
        
        async def get_logs(self, limit: int = 100, offset: int = 0, 
                          event_type: str = None, user_id: str = None):
            filtered_logs = self.logs
            
            if event_type:
                filtered_logs = [log for log in filtered_logs if log["event_type"] == event_type]
            
            if user_id:
                filtered_logs = [log for log in filtered_logs if log["user_id"] == user_id]
            
            return filtered_logs[offset:offset + limit]
        
        async def get_user_activity(self, user_id: str, days: int = 30):
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            return [
                log for log in self.logs 
                if log["user_id"] == user_id and 
                datetime.fromisoformat(log["timestamp"]) > cutoff_date
            ]
    
    return MockAuditLogger()

@pytest.fixture(scope="function")
def mock_rate_limiter():
    """Mock rate limiter for testing"""
    
    class MockRateLimiter:
        def __init__(self):
            self.requests = {}  # key -> list of timestamps
            self.blocked_ips = set()
        
        async def check_rate_limit(self, key: str, limit: int = 60, window: int = 60):
            """Check if request is within rate limit"""
            now = datetime.utcnow().timestamp()
            
            if key in self.blocked_ips:
                return False, "IP blocked"
            
            if key not in self.requests:
                self.requests[key] = []
            
            # Remove old requests outside the window
            window_start = now - window
            self.requests[key] = [
                timestamp for timestamp in self.requests[key] 
                if timestamp > window_start
            ]
            
            # Check if within limit
            if len(self.requests[key]) >= limit:
                return False, "Rate limit exceeded"
            
            # Add current request
            self.requests[key].append(now)
            return True, "OK"
        
        async def block_ip(self, ip: str, duration: int = 3600):
            """Block IP address"""
            self.blocked_ips.add(ip)
            return True
        
        async def unblock_ip(self, ip: str):
            """Unblock IP address"""
            self.blocked_ips.discard(ip)
            return True
        
        async def get_request_count(self, key: str, window: int = 60):
            """Get current request count for key"""
            if key not in self.requests:
                return 0
            
            now = datetime.utcnow().timestamp()
            window_start = now - window
            
            return len([
                timestamp for timestamp in self.requests[key]
                if timestamp > window_start
            ])
    
    return MockRateLimiter()

@pytest.fixture(scope="function")
def security_test_app():
    """Create FastAPI test application with security components"""
    from fastapi import FastAPI, Depends, HTTPException, Request
    from fastapi.security import HTTPBearer
    
    app = FastAPI(title="Security Test App")
    security = HTTPBearer()
    
    # Add mock services to app state
    app.state.database = None  # Will be set by individual tests
    app.state.redis = None
    app.state.jwt_service = None
    app.state.encryption_service = None
    app.state.audit_logger = None
    app.state.rate_limiter = None
    
    # Test routes
    @app.post("/api/test/login")
    async def test_login(credentials: dict):
        return {"message": "Login endpoint", "data": credentials}
    
    @app.get("/api/test/protected")
    async def test_protected(token: str = Depends(security)):
        return {"message": "Protected endpoint", "token": token.credentials}
    
    @app.get("/api/test/admin")
    async def test_admin():
        return {"message": "Admin endpoint"}
    
    @app.post("/api/test/data")
    async def test_data(data: dict):
        return {"message": "Data endpoint", "received": data}
    
    return app

@pytest.fixture(scope="function")
def test_client(security_test_app, mock_database, mock_redis, mock_jwt_service, 
               mock_encryption_service, mock_audit_logger, mock_rate_limiter):
    """Create test client with all security mocks"""
    from fastapi.testclient import TestClient
    
    # Inject mock services
    security_test_app.state.database = mock_database
    security_test_app.state.redis = mock_redis
    security_test_app.state.jwt_service = mock_jwt_service
    security_test_app.state.encryption_service = mock_encryption_service
    security_test_app.state.audit_logger = mock_audit_logger
    security_test_app.state.rate_limiter = mock_rate_limiter
    
    return TestClient(security_test_app)

# Test data generators
class SecurityTestDataGenerator:
    """Generate test data for security tests"""
    
    @staticmethod
    def generate_test_user(role="guest", active=True):
        """Generate test user data"""
        user_id = f"test_user_{secrets.token_hex(4)}"
        username = f"testuser_{secrets.token_hex(4)}"
        
        return {
            "user_id": user_id,
            "username": username,
            "email": f"{username}@test.com",
            "password_hash": "$2b$12$test_hash",
            "roles": [role],
            "is_active": active,
            "mfa_enabled": False,
            "created_at": datetime.utcnow().isoformat(),
            "last_login": None
        }
    
    @staticmethod
    def generate_jwt_payload(user_id, username, roles=None):
        """Generate JWT payload"""
        return {
            "sub": user_id,
            "username": username,
            "roles": roles or ["guest"],
            "iat": datetime.utcnow().timestamp(),
            "exp": (datetime.utcnow() + timedelta(hours=1)).timestamp()
        }
    
    @staticmethod
    def generate_audit_event(event_type, user_id=None):
        """Generate audit event data"""
        return {
            "event_type": event_type,
            "user_id": user_id,
            "details": {"test": "data"},
            "ip_address": "192.168.1.100",
            "user_agent": "Test Agent"
        }
    
    @staticmethod
    def generate_malicious_payloads():
        """Generate common attack payloads for testing"""
        return {
            "sql_injection": [
                "' OR '1'='1",
                "'; DROP TABLE users;--",
                "' UNION SELECT * FROM users--"
            ],
            "xss": [
                "<script>alert('XSS')</script>",
                "<img src=x onerror=alert('XSS')>",
                "javascript:alert('XSS')"
            ],
            "path_traversal": [
                "../../../etc/passwd",
                "..\\..\\..\\windows\\system32\\config\\sam",
                "....//....//....//etc/passwd"
            ],
            "command_injection": [
                "; ls -la",
                "| cat /etc/passwd",
                "&& rm -rf /"
            ]
        }

@pytest.fixture
def test_data_generator():
    """Provide test data generator"""
    return SecurityTestDataGenerator()

# Test utilities
class SecurityTestUtils:
    """Utility functions for security tests"""
    
    @staticmethod
    def create_temp_file(content="", suffix=".tmp"):
        """Create temporary file for testing"""
        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix=suffix, delete=False)
        temp_file.write(content)
        temp_file.close()
        return temp_file.name
    
    @staticmethod
    def cleanup_temp_file(filepath):
        """Clean up temporary file"""
        try:
            os.unlink(filepath)
        except:
            pass
    
    @staticmethod
    def measure_execution_time(func, *args, **kwargs):
        """Measure function execution time"""
        import time
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        return result, end_time - start_time
    
    @staticmethod
    def generate_large_payload(size_mb=1):
        """Generate large payload for testing"""
        # Generate 1MB of data by default
        size_bytes = size_mb * 1024 * 1024
        return "A" * size_bytes

@pytest.fixture
def test_utils():
    """Provide test utilities"""
    return SecurityTestUtils()

# Pytest configuration
def pytest_configure(config):
    """Configure pytest for security tests"""
    # Add custom markers
    config.addinivalue_line(
        "markers", "security: mark test as security related"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as integration test"
    )
    config.addinivalue_line(
        "markers", "penetration: mark test as penetration test"
    )

# Test session hooks
@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Set up test environment"""
    # Set test environment variables
    os.environ["TESTING"] = "1"
    os.environ["LOG_LEVEL"] = "DEBUG"
    
    yield
    
    # Cleanup after tests
    if "TESTING" in os.environ:
        del os.environ["TESTING"]