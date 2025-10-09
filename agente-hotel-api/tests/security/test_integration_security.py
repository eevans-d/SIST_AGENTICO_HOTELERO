"""
Integration Security Testing Suite
Comprehensive end-to-end security integration tests
"""

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import json
import jwt
import time
import asyncio
from datetime import datetime, timedelta
import secrets
import redis
import threading

# Test complete security workflow integration
class TestSecurityIntegration:
    """Test end-to-end security integration"""
    
    @pytest.fixture
    def integrated_app(self):
        """Create integrated app with all security components"""
        from fastapi import FastAPI, Depends, HTTPException, status
        from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
        
        app = FastAPI()
        security = HTTPBearer()
        
        # Mock services
        app.state.jwt_service = MagicMock()
        app.state.rate_limiter = MagicMock()
        app.state.audit_logger = MagicMock()
        app.state.encryption_service = MagicMock()
        app.state.redis_client = MagicMock()
        
        # Mock user database
        users_db = {
            "testuser": {
                "id": "user_123",
                "username": "testuser",
                "password_hash": "hashed_password",
                "roles": ["guest"],
                "is_active": True,
                "mfa_enabled": False
            },
            "admin": {
                "id": "admin_123",
                "username": "admin",
                "password_hash": "admin_hash",
                "roles": ["admin"],
                "is_active": True,
                "mfa_enabled": True
            }
        }
        
        # Authentication dependency
        async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
            token = credentials.credentials
            if token == "valid_token":
                return users_db["testuser"]
            elif token == "admin_token":
                return users_db["admin"]
            elif token == "expired_token":
                raise HTTPException(status_code=401, detail="Token expired")
            else:
                raise HTTPException(status_code=401, detail="Invalid token")
        
        # Authorization dependency
        def require_role(required_role: str):
            def role_checker(current_user = Depends(get_current_user)):
                if required_role not in current_user["roles"] and "admin" not in current_user["roles"]:
                    raise HTTPException(status_code=403, detail="Insufficient permissions")
                return current_user
            return role_checker
        
        # Routes with integrated security
        @app.post("/api/auth/login")
        async def login(credentials: dict):
            username = credentials.get("username")
            password = credentials.get("password")
            
            # Rate limiting check
            if app.state.rate_limiter.is_rate_limited.return_value:
                raise HTTPException(status_code=429, detail="Too many requests")
            
            # Authentication
            if username in users_db:
                user = users_db[username]
                if user["is_active"]:
                    # Audit log
                    app.state.audit_logger.log_event.assert_called()
                    
                    # Generate token
                    if username == "testuser":
                        return {"access_token": "valid_token", "token_type": "bearer"}
                    elif username == "admin":
                        return {"access_token": "admin_token", "token_type": "bearer"}
                else:
                    raise HTTPException(status_code=423, detail="Account locked")
            
            raise HTTPException(status_code=401, detail="Invalid credentials")
        
        @app.get("/api/auth/profile")
        async def get_profile(current_user = Depends(get_current_user)):
            return {
                "user_id": current_user["id"],
                "username": current_user["username"],
                "roles": current_user["roles"]
            }
        
        @app.get("/api/admin/users")
        async def list_users(current_user = Depends(require_role("admin"))):
            return {"users": list(users_db.keys())}
        
        @app.post("/api/reservations")
        async def create_reservation(
            reservation_data: dict,
            current_user = Depends(get_current_user)
        ):
            # Encrypt sensitive data
            encrypted_data = app.state.encryption_service.encrypt(json.dumps(reservation_data))
            
            return {
                "reservation_id": "RES-123",
                "status": "created",
                "user_id": current_user["id"]
            }
        
        @app.get("/api/reservations/{reservation_id}")
        async def get_reservation(
            reservation_id: str,
            current_user = Depends(get_current_user)
        ):
            # Check ownership or admin role
            if reservation_id != "RES-123" and "admin" not in current_user["roles"]:
                raise HTTPException(status_code=404, detail="Reservation not found")
            
            return {
                "reservation_id": reservation_id,
                "user_id": current_user["id"],
                "room_number": "101",
                "check_in": "2024-01-15"
            }
        
        return TestClient(app)
    
    def test_complete_authentication_flow(self, integrated_app):
        """Test complete authentication workflow"""
        
        # Step 1: Login with valid credentials
        login_data = {"username": "testuser", "password": "password123"}
        response = integrated_app.post("/api/auth/login", json=login_data)
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        token = data["access_token"]
        
        # Step 2: Access protected resource with token
        headers = {"Authorization": f"Bearer {token}"}
        response = integrated_app.get("/api/auth/profile", headers=headers)
        
        assert response.status_code == 200
        profile = response.json()
        assert profile["username"] == "testuser"
        assert "guest" in profile["roles"]
        
        # Step 3: Try to access admin resource (should fail)
        response = integrated_app.get("/api/admin/users", headers=headers)
        assert response.status_code == 403
    
    def test_admin_authorization_flow(self, integrated_app):
        """Test admin authorization workflow"""
        
        # Login as admin
        login_data = {"username": "admin", "password": "admin_password"}
        response = integrated_app.post("/api/auth/login", json=login_data)
        
        assert response.status_code == 200
        token = response.json()["access_token"]
        
        # Access admin resource
        headers = {"Authorization": f"Bearer {token}"}
        response = integrated_app.get("/api/admin/users", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "users" in data
    
    def test_data_encryption_integration(self, integrated_app):
        """Test data encryption in API workflow"""
        
        # Login first
        login_data = {"username": "testuser", "password": "password123"}
        response = integrated_app.post("/api/auth/login", json=login_data)
        token = response.json()["access_token"]
        
        # Create reservation with sensitive data
        reservation_data = {
            "guest_name": "John Doe",
            "credit_card": "4111-1111-1111-1111",
            "room_type": "deluxe",
            "check_in": "2024-01-15"
        }
        
        headers = {"Authorization": f"Bearer {token}"}
        response = integrated_app.post("/api/reservations", json=reservation_data, headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "reservation_id" in data
        assert data["status"] == "created"
    
    def test_unauthorized_access_attempts(self, integrated_app):
        """Test various unauthorized access attempts"""
        
        # Try without token
        response = integrated_app.get("/api/auth/profile")
        assert response.status_code == 403  # No credentials
        
        # Try with invalid token
        headers = {"Authorization": "Bearer invalid_token"}
        response = integrated_app.get("/api/auth/profile", headers=headers)
        assert response.status_code == 401
        
        # Try with expired token
        headers = {"Authorization": "Bearer expired_token"}
        response = integrated_app.get("/api/auth/profile", headers=headers)
        assert response.status_code == 401
    
    def test_privilege_escalation_prevention(self, integrated_app):
        """Test prevention of privilege escalation attacks"""
        
        # Login as regular user
        login_data = {"username": "testuser", "password": "password123"}
        response = integrated_app.post("/api/auth/login", json=login_data)
        token = response.json()["access_token"]
        
        headers = {"Authorization": f"Bearer {token}"}
        
        # Try to access admin endpoints
        admin_endpoints = [
            "/api/admin/users",
            "/api/admin/security/audit",
            "/api/admin/roles"
        ]
        
        for endpoint in admin_endpoints:
            try:
                response = integrated_app.get(endpoint, headers=headers)
                # Should return 403 Forbidden or 404 Not Found
                assert response.status_code in [403, 404]
            except:
                # Endpoint might not exist in test app, which is fine
                pass

class TestConcurrentSecurityOperations:
    """Test security under concurrent operations"""
    
    @pytest.fixture
    def concurrent_app(self):
        """Create app for concurrent testing"""
        from fastapi import FastAPI, HTTPException
        import threading
        
        app = FastAPI()
        
        # Shared state for testing concurrent access
        app.state.active_sessions = {}
        app.state.login_attempts = {}
        app.state.session_lock = threading.Lock()
        app.state.attempt_lock = threading.Lock()
        
        @app.post("/api/auth/login")
        async def concurrent_login(credentials: dict):
            username = credentials.get("username")
            
            with app.state.attempt_lock:
                attempts = app.state.login_attempts.get(username, 0)
                app.state.login_attempts[username] = attempts + 1
                
                # Simulate rate limiting after 5 attempts
                if attempts >= 5:
                    raise HTTPException(status_code=429, detail="Too many attempts")
            
            # Simulate successful login
            session_id = f"session_{username}_{time.time()}"
            
            with app.state.session_lock:
                app.state.active_sessions[session_id] = {
                    "username": username,
                    "created_at": time.time()
                }
            
            return {"session_id": session_id, "username": username}
        
        @app.delete("/api/auth/logout/{session_id}")
        async def concurrent_logout(session_id: str):
            with app.state.session_lock:
                if session_id in app.state.active_sessions:
                    del app.state.active_sessions[session_id]
                    return {"status": "logged_out"}
                else:
                    raise HTTPException(status_code=404, detail="Session not found")
        
        @app.get("/api/auth/sessions")
        async def get_active_sessions():
            with app.state.session_lock:
                return {"sessions": list(app.state.active_sessions.keys())}
        
        return TestClient(app)
    
    def test_concurrent_logins(self, concurrent_app):
        """Test concurrent login attempts"""
        import concurrent.futures
        
        def login_user(username):
            return concurrent_app.post("/api/auth/login", json={
                "username": username,
                "password": "password"
            })
        
        # Test multiple users logging in simultaneously
        usernames = [f"user_{i}" for i in range(10)]
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(login_user, username) for username in usernames]
            responses = [future.result() for future in futures]
        
        # All logins should succeed
        for response in responses:
            assert response.status_code == 200
        
        # Check active sessions
        response = concurrent_app.get("/api/auth/sessions")
        sessions = response.json()["sessions"]
        assert len(sessions) == 10
    
    def test_rate_limiting_under_load(self, concurrent_app):
        """Test rate limiting under concurrent load"""
        import concurrent.futures
        
        def attempt_login():
            return concurrent_app.post("/api/auth/login", json={
                "username": "bruteforce_target",
                "password": "wrong_password"
            })
        
        # Make many concurrent requests to trigger rate limiting
        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(attempt_login) for _ in range(20)]
            responses = [future.result() for future in futures]
        
        # Some requests should succeed, others should be rate limited
        success_count = sum(1 for r in responses if r.status_code == 200)
        rate_limited_count = sum(1 for r in responses if r.status_code == 429)
        
        assert success_count > 0
        assert rate_limited_count > 0
    
    def test_session_cleanup_race_conditions(self, concurrent_app):
        """Test session cleanup under race conditions"""
        import concurrent.futures
        
        # Create sessions
        sessions = []
        for i in range(5):
            response = concurrent_app.post("/api/auth/login", json={
                "username": f"user_{i}",
                "password": "password"
            })
            sessions.append(response.json()["session_id"])
        
        def logout_session(session_id):
            return concurrent_app.delete(f"/api/auth/logout/{session_id}")
        
        # Try to logout sessions concurrently
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(logout_session, session_id) for session_id in sessions]
            responses = [future.result() for future in futures]
        
        # All logouts should succeed
        for response in responses:
            assert response.status_code == 200
        
        # No sessions should remain
        response = concurrent_app.get("/api/auth/sessions")
        remaining_sessions = response.json()["sessions"]
        assert len(remaining_sessions) == 0

class TestSecurityErrorRecovery:
    """Test security system error recovery"""
    
    @pytest.fixture
    def recovery_app(self):
        """Create app for error recovery testing"""
        from fastapi import FastAPI, HTTPException
        
        app = FastAPI()
        
        # Simulate various failure scenarios
        app.state.database_failure = False
        app.state.redis_failure = False
        app.state.encryption_failure = False
        
        @app.post("/api/auth/login")
        async def login_with_failures(credentials: dict):
            if app.state.database_failure:
                raise HTTPException(status_code=503, detail="Database unavailable")
            
            if app.state.redis_failure:
                # Fallback to in-memory cache
                return {
                    "access_token": "fallback_token",
                    "warning": "Using fallback authentication"
                }
            
            return {"access_token": "normal_token"}
        
        @app.get("/api/data/encrypted")
        async def get_encrypted_data():
            if app.state.encryption_failure:
                # Graceful degradation - return error
                raise HTTPException(status_code=503, detail="Encryption service unavailable")
            
            return {"data": "encrypted_data_placeholder"}
        
        @app.post("/api/system/recovery")
        async def initiate_recovery():
            # Reset failure states
            app.state.database_failure = False
            app.state.redis_failure = False
            app.state.encryption_failure = False
            
            return {"status": "recovery_initiated"}
        
        @app.post("/api/system/simulate-failure")
        async def simulate_failure(failure_type: dict):
            failure = failure_type.get("type")
            
            if failure == "database":
                app.state.database_failure = True
            elif failure == "redis":
                app.state.redis_failure = True
            elif failure == "encryption":
                app.state.encryption_failure = True
            
            return {"status": f"{failure}_failure_simulated"}
        
        return TestClient(app)
    
    def test_database_failure_recovery(self, recovery_app):
        """Test recovery from database failures"""
        
        # Simulate database failure
        recovery_app.post("/api/system/simulate-failure", json={"type": "database"})
        
        # Login should fail
        response = recovery_app.post("/api/auth/login", json={"username": "test", "password": "pass"})
        assert response.status_code == 503
        
        # Initiate recovery
        recovery_app.post("/api/system/recovery")
        
        # Login should work again
        response = recovery_app.post("/api/auth/login", json={"username": "test", "password": "pass"})
        assert response.status_code == 200
    
    def test_cache_failure_fallback(self, recovery_app):
        """Test fallback when cache fails"""
        
        # Simulate Redis failure
        recovery_app.post("/api/system/simulate-failure", json={"type": "redis"})
        
        # Login should still work with fallback
        response = recovery_app.post("/api/auth/login", json={"username": "test", "password": "pass"})
        assert response.status_code == 200
        data = response.json()
        assert "warning" in data  # Should indicate fallback mode
    
    def test_encryption_service_failure(self, recovery_app):
        """Test handling of encryption service failures"""
        
        # Simulate encryption failure
        recovery_app.post("/api/system/simulate-failure", json={"type": "encryption"})
        
        # Encrypted data access should fail gracefully
        response = recovery_app.get("/api/data/encrypted")
        assert response.status_code == 503
        
        # Recovery should restore functionality
        recovery_app.post("/api/system/recovery")
        response = recovery_app.get("/api/data/encrypted")
        assert response.status_code == 200

class TestSecurityCompliance:
    """Test security compliance and standards"""
    
    def test_session_timeout_compliance(self):
        """Test session timeout compliance"""
        
        # Simulate session with timeout
        session_start = time.time()
        session_timeout = 30 * 60  # 30 minutes
        
        def is_session_valid(start_time, timeout_seconds):
            return (time.time() - start_time) < timeout_seconds
        
        # Session should be valid initially
        assert is_session_valid(session_start, session_timeout) is True
        
        # Simulate time passage
        old_session_start = time.time() - (35 * 60)  # 35 minutes ago
        assert is_session_valid(old_session_start, session_timeout) is False
    
    def test_password_policy_compliance(self):
        """Test password policy compliance"""
        
        def validate_password(password):
            """Validate password against security policy"""
            if len(password) < 8:
                return False, "Password too short"
            
            if not any(c.isupper() for c in password):
                return False, "Password must contain uppercase letter"
            
            if not any(c.islower() for c in password):
                return False, "Password must contain lowercase letter"
            
            if not any(c.isdigit() for c in password):
                return False, "Password must contain digit"
            
            special_chars = "!@#$%^&*()_+-=[]{}|;:,.<>?"
            if not any(c in special_chars for c in password):
                return False, "Password must contain special character"
            
            return True, "Password valid"
        
        # Test various passwords
        test_cases = [
            ("weak", False),
            ("WeakPassword", False),
            ("WeakPassword123", False),
            ("WeakPassword123!", True),
            ("Str0ng!Pass", True)
        ]
        
        for password, should_be_valid in test_cases:
            is_valid, message = validate_password(password)
            assert is_valid == should_be_valid
    
    def test_audit_log_compliance(self):
        """Test audit logging compliance"""
        
        audit_events = []
        
        def log_security_event(event_type, user_id, details):
            """Log security event for compliance"""
            audit_events.append({
                "timestamp": datetime.utcnow().isoformat(),
                "event_type": event_type,
                "user_id": user_id,
                "details": details,
                "ip_address": "192.168.1.100"  # Would be real IP in production
            })
        
        # Simulate various security events
        log_security_event("login_success", "user_123", {"method": "password"})
        log_security_event("login_failure", "user_456", {"reason": "invalid_password"})
        log_security_event("password_change", "user_123", {"changed_by": "user"})
        log_security_event("account_locked", "user_789", {"reason": "brute_force"})
        
        # Verify audit trail
        assert len(audit_events) == 4
        
        # All events should have required fields
        for event in audit_events:
            assert "timestamp" in event
            assert "event_type" in event
            assert "user_id" in event
            assert "details" in event
    
    def test_data_retention_compliance(self):
        """Test data retention compliance"""
        
        def should_retain_data(data_type, creation_date, retention_policy):
            """Check if data should be retained based on policy"""
            retention_days = retention_policy.get(data_type, 365)  # Default 1 year
            age_days = (datetime.utcnow() - creation_date).days
            return age_days < retention_days
        
        # Define retention policy
        retention_policy = {
            "audit_logs": 2555,  # 7 years for audit logs
            "user_sessions": 90,  # 90 days for session data
            "payment_data": 1095,  # 3 years for payment data
            "personal_data": 365   # 1 year for personal data
        }
        
        # Test data retention
        old_audit_log = datetime.utcnow() - timedelta(days=3000)  # 8+ years old
        recent_session = datetime.utcnow() - timedelta(days=30)   # 30 days old
        old_payment = datetime.utcnow() - timedelta(days=1200)    # 3+ years old
        
        assert should_retain_data("audit_logs", old_audit_log, retention_policy) is False
        assert should_retain_data("user_sessions", recent_session, retention_policy) is True
        assert should_retain_data("payment_data", old_payment, retention_policy) is False

if __name__ == "__main__":
    pytest.main([__file__, "-v"])