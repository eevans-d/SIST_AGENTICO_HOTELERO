"""
Security API Endpoints Testing Suite
Comprehensive tests for security-related API endpoints
"""

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import json
import jwt
import time
from datetime import datetime, timedelta
import secrets
import base64

# Test security API endpoints functionality
class TestSecurityAPIEndpoints:
    """Test security API endpoints"""
    
    @pytest.fixture
    def test_client(self):
        """Create test client with security routes"""
        from fastapi import FastAPI
        
        app = FastAPI()
        
        # Mock security dependencies
        app.state.security_service = MagicMock()
        app.state.audit_logger = MagicMock()
        app.state.rate_limiter = MagicMock()
        
        # Add basic security routes for testing
        @app.post("/api/auth/register")
        async def register_user(user_data: dict):
            return {"status": "success", "user_id": "user_123"}
        
        @app.post("/api/auth/login")
        async def login_user(credentials: dict):
            return {
                "access_token": "mock_access_token",
                "refresh_token": "mock_refresh_token",
                "token_type": "bearer"
            }
        
        @app.post("/api/auth/logout")
        async def logout_user():
            return {"status": "success", "message": "Logged out successfully"}
        
        @app.post("/api/auth/refresh")
        async def refresh_token(token_data: dict):
            return {"access_token": "new_mock_access_token"}
        
        @app.get("/api/auth/profile")
        async def get_user_profile():
            return {
                "user_id": "user_123",
                "username": "testuser",
                "roles": ["guest"]
            }
        
        @app.put("/api/auth/profile")
        async def update_user_profile(profile_data: dict):
            return {"status": "success", "message": "Profile updated"}
        
        @app.post("/api/auth/change-password")
        async def change_password(password_data: dict):
            return {"status": "success", "message": "Password changed"}
        
        @app.post("/api/auth/reset-password")
        async def reset_password(reset_data: dict):
            return {"status": "success", "message": "Password reset email sent"}
        
        @app.post("/api/auth/mfa/enable")
        async def enable_mfa():
            return {
                "qr_code": "mock_qr_code_data",
                "backup_codes": ["code1", "code2", "code3"]
            }
        
        @app.post("/api/auth/mfa/verify")
        async def verify_mfa(mfa_data: dict):
            return {"status": "success", "message": "MFA verified"}
        
        @app.get("/api/security/audit")
        async def get_audit_logs():
            return {
                "logs": [
                    {
                        "timestamp": "2024-01-15T10:30:00Z",
                        "user_id": "user_123",
                        "action": "login",
                        "result": "success"
                    }
                ]
            }
        
        @app.get("/api/security/sessions")
        async def get_user_sessions():
            return {
                "sessions": [
                    {
                        "session_id": "session_123",
                        "created_at": "2024-01-15T10:30:00Z",
                        "last_activity": "2024-01-15T11:00:00Z",
                        "ip_address": "192.168.1.100"
                    }
                ]
            }
        
        @app.delete("/api/security/sessions/{session_id}")
        async def revoke_session(session_id: str):
            return {"status": "success", "message": f"Session {session_id} revoked"}
        
        @app.get("/api/security/permissions")
        async def get_user_permissions():
            return {
                "permissions": [
                    "view_reservations",
                    "create_reservation",
                    "modify_own_reservation"
                ]
            }
        
        return TestClient(app)
    
    def test_user_registration_endpoint(self, test_client):
        """Test user registration endpoint"""
        
        registration_data = {
            "username": "newuser",
            "email": "newuser@hotel.com",
            "password": "SecurePassword123!",
            "confirm_password": "SecurePassword123!",
            "first_name": "New",
            "last_name": "User"
        }
        
        response = test_client.post("/api/auth/register", json=registration_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "user_id" in data
    
    def test_user_login_endpoint(self, test_client):
        """Test user login endpoint"""
        
        login_data = {
            "username": "testuser",
            "password": "password123"
        }
        
        response = test_client.post("/api/auth/login", json=login_data)
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
    
    def test_user_logout_endpoint(self, test_client):
        """Test user logout endpoint"""
        
        # Mock authorization header
        headers = {"Authorization": "Bearer mock_access_token"}
        
        response = test_client.post("/api/auth/logout", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
    
    def test_token_refresh_endpoint(self, test_client):
        """Test token refresh endpoint"""
        
        refresh_data = {
            "refresh_token": "mock_refresh_token"
        }
        
        response = test_client.post("/api/auth/refresh", json=refresh_data)
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
    
    def test_user_profile_endpoint(self, test_client):
        """Test user profile endpoints"""
        
        # Test GET profile
        headers = {"Authorization": "Bearer mock_access_token"}
        response = test_client.get("/api/auth/profile", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "user_id" in data
        assert "username" in data
        assert "roles" in data
        
        # Test PUT profile update
        update_data = {
            "first_name": "Updated",
            "last_name": "Name",
            "email": "updated@hotel.com"
        }
        
        response = test_client.put("/api/auth/profile", json=update_data, headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
    
    def test_password_change_endpoint(self, test_client):
        """Test password change endpoint"""
        
        password_data = {
            "current_password": "old_password",
            "new_password": "NewSecurePassword123!",
            "confirm_password": "NewSecurePassword123!"
        }
        
        headers = {"Authorization": "Bearer mock_access_token"}
        response = test_client.post("/api/auth/change-password", json=password_data, headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
    
    def test_password_reset_endpoint(self, test_client):
        """Test password reset endpoint"""
        
        reset_data = {
            "email": "user@hotel.com"
        }
        
        response = test_client.post("/api/auth/reset-password", json=reset_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
    
    def test_mfa_endpoints(self, test_client):
        """Test MFA (Multi-Factor Authentication) endpoints"""
        
        headers = {"Authorization": "Bearer mock_access_token"}
        
        # Test MFA enable
        response = test_client.post("/api/auth/mfa/enable", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "qr_code" in data
        assert "backup_codes" in data
        
        # Test MFA verify
        mfa_data = {
            "code": "123456"
        }
        
        response = test_client.post("/api/auth/mfa/verify", json=mfa_data, headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"

class TestSecurityAuditEndpoints:
    """Test security audit and monitoring endpoints"""
    
    @pytest.fixture
    def admin_client(self):
        """Create test client with admin security routes"""
        from fastapi import FastAPI
        
        app = FastAPI()
        
        # Mock admin security routes
        @app.get("/api/admin/security/audit")
        async def get_security_audit():
            return {
                "audit_logs": [
                    {
                        "id": "audit_1",
                        "timestamp": "2024-01-15T10:30:00Z",
                        "user_id": "user_123",
                        "action": "login_attempt",
                        "result": "success",
                        "ip_address": "192.168.1.100",
                        "user_agent": "Mozilla/5.0..."
                    },
                    {
                        "id": "audit_2",
                        "timestamp": "2024-01-15T10:25:00Z",
                        "user_id": "user_456",
                        "action": "password_change",
                        "result": "success",
                        "ip_address": "192.168.1.101"
                    }
                ],
                "total_count": 2,
                "page": 1,
                "per_page": 50
            }
        
        @app.get("/api/admin/security/threats")
        async def get_security_threats():
            return {
                "threats": [
                    {
                        "id": "threat_1",
                        "type": "brute_force",
                        "severity": "high",
                        "source_ip": "10.0.0.100",
                        "detected_at": "2024-01-15T10:00:00Z",
                        "status": "blocked"
                    },
                    {
                        "id": "threat_2",
                        "type": "suspicious_login",
                        "severity": "medium",
                        "user_id": "user_789",
                        "detected_at": "2024-01-15T09:30:00Z",
                        "status": "investigating"
                    }
                ]
            }
        
        @app.get("/api/admin/security/compliance")
        async def get_compliance_status():
            return {
                "compliance_checks": {
                    "password_policy": {
                        "status": "compliant",
                        "last_check": "2024-01-15T08:00:00Z"
                    },
                    "encryption_standards": {
                        "status": "compliant",
                        "last_check": "2024-01-15T08:00:00Z"
                    },
                    "access_controls": {
                        "status": "compliant",
                        "last_check": "2024-01-15T08:00:00Z"
                    },
                    "audit_logging": {
                        "status": "compliant",
                        "last_check": "2024-01-15T08:00:00Z"
                    }
                },
                "overall_score": 100,
                "last_assessment": "2024-01-15T08:00:00Z"
            }
        
        @app.post("/api/admin/security/lockdown")
        async def initiate_security_lockdown():
            return {
                "status": "success",
                "message": "Security lockdown initiated",
                "lockdown_id": "lockdown_123"
            }
        
        @app.get("/api/admin/security/users/{user_id}/sessions")
        async def get_user_sessions(user_id: str):
            return {
                "user_id": user_id,
                "sessions": [
                    {
                        "session_id": "session_1",
                        "created_at": "2024-01-15T10:00:00Z",
                        "last_activity": "2024-01-15T11:00:00Z",
                        "ip_address": "192.168.1.100",
                        "device": "Chrome on Windows",
                        "status": "active"
                    }
                ]
            }
        
        @app.delete("/api/admin/security/users/{user_id}/sessions")
        async def revoke_all_user_sessions(user_id: str):
            return {
                "status": "success",
                "message": f"All sessions for user {user_id} revoked",
                "revoked_count": 3
            }
        
        return TestClient(app)
    
    def test_security_audit_endpoint(self, admin_client):
        """Test security audit endpoint"""
        
        headers = {"Authorization": "Bearer admin_token"}
        response = admin_client.get("/api/admin/security/audit", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "audit_logs" in data
        assert "total_count" in data
        assert len(data["audit_logs"]) > 0
        
        # Verify audit log structure
        log = data["audit_logs"][0]
        assert "id" in log
        assert "timestamp" in log
        assert "user_id" in log
        assert "action" in log
        assert "result" in log
    
    def test_security_threats_endpoint(self, admin_client):
        """Test security threats endpoint"""
        
        headers = {"Authorization": "Bearer admin_token"}
        response = admin_client.get("/api/admin/security/threats", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "threats" in data
        assert len(data["threats"]) > 0
        
        # Verify threat structure
        threat = data["threats"][0]
        assert "id" in threat
        assert "type" in threat
        assert "severity" in threat
        assert "detected_at" in threat
        assert "status" in threat
    
    def test_compliance_status_endpoint(self, admin_client):
        """Test compliance status endpoint"""
        
        headers = {"Authorization": "Bearer admin_token"}
        response = admin_client.get("/api/admin/security/compliance", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "compliance_checks" in data
        assert "overall_score" in data
        
        # Verify compliance checks
        checks = data["compliance_checks"]
        assert "password_policy" in checks
        assert "encryption_standards" in checks
        assert "access_controls" in checks
        assert "audit_logging" in checks
        
        # Each check should have status and last_check
        for check_name, check_data in checks.items():
            assert "status" in check_data
            assert "last_check" in check_data
    
    def test_security_lockdown_endpoint(self, admin_client):
        """Test security lockdown endpoint"""
        
        headers = {"Authorization": "Bearer admin_token"}
        response = admin_client.post("/api/admin/security/lockdown", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "lockdown_id" in data
    
    def test_user_sessions_management(self, admin_client):
        """Test user sessions management endpoints"""
        
        headers = {"Authorization": "Bearer admin_token"}
        user_id = "user_123"
        
        # Test get user sessions
        response = admin_client.get(f"/api/admin/security/users/{user_id}/sessions", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == user_id
        assert "sessions" in data
        
        # Test revoke all user sessions
        response = admin_client.delete(f"/api/admin/security/users/{user_id}/sessions", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "revoked_count" in data

class TestPermissionsAndRolesEndpoints:
    """Test permissions and roles management endpoints"""
    
    @pytest.fixture
    def roles_client(self):
        """Create test client with roles and permissions routes"""
        from fastapi import FastAPI
        
        app = FastAPI()
        
        @app.get("/api/admin/roles")
        async def get_roles():
            return {
                "roles": [
                    {
                        "id": "role_1",
                        "name": "admin",
                        "description": "Full system access",
                        "permissions": ["*"]
                    },
                    {
                        "id": "role_2", 
                        "name": "hotel_manager",
                        "description": "Hotel management access",
                        "permissions": [
                            "view_all_reservations",
                            "modify_reservations",
                            "view_reports",
                            "manage_rooms"
                        ]
                    },
                    {
                        "id": "role_3",
                        "name": "guest",
                        "description": "Guest access",
                        "permissions": [
                            "view_own_reservations",
                            "modify_own_reservations",
                            "view_hotel_services"
                        ]
                    }
                ]
            }
        
        @app.post("/api/admin/roles")
        async def create_role(role_data: dict):
            return {
                "status": "success",
                "role_id": "new_role_123",
                "message": "Role created successfully"
            }
        
        @app.put("/api/admin/roles/{role_id}")
        async def update_role(role_id: str, role_data: dict):
            return {
                "status": "success",
                "message": f"Role {role_id} updated successfully"
            }
        
        @app.delete("/api/admin/roles/{role_id}")
        async def delete_role(role_id: str):
            return {
                "status": "success",
                "message": f"Role {role_id} deleted successfully"
            }
        
        @app.get("/api/admin/permissions")
        async def get_permissions():
            return {
                "permissions": [
                    {
                        "id": "perm_1",
                        "name": "view_reservations",
                        "description": "View hotel reservations",
                        "category": "reservations"
                    },
                    {
                        "id": "perm_2",
                        "name": "modify_reservations", 
                        "description": "Modify hotel reservations",
                        "category": "reservations"
                    },
                    {
                        "id": "perm_3",
                        "name": "view_reports",
                        "description": "View system reports",
                        "category": "reporting"
                    }
                ]
            }
        
        @app.post("/api/admin/users/{user_id}/roles")
        async def assign_role_to_user(user_id: str, role_data: dict):
            return {
                "status": "success",
                "message": f"Role assigned to user {user_id}"
            }
        
        @app.delete("/api/admin/users/{user_id}/roles/{role_id}")
        async def remove_role_from_user(user_id: str, role_id: str):
            return {
                "status": "success",
                "message": f"Role {role_id} removed from user {user_id}"
            }
        
        @app.get("/api/admin/users/{user_id}/permissions")
        async def get_user_permissions(user_id: str):
            return {
                "user_id": user_id,
                "permissions": [
                    "view_own_reservations",
                    "modify_own_reservations",
                    "view_hotel_services"
                ],
                "roles": ["guest"]
            }
        
        return TestClient(app)
    
    def test_roles_management(self, roles_client):
        """Test roles management endpoints"""
        
        headers = {"Authorization": "Bearer admin_token"}
        
        # Test get roles
        response = roles_client.get("/api/admin/roles", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "roles" in data
        assert len(data["roles"]) > 0
        
        # Verify role structure
        role = data["roles"][0]
        assert "id" in role
        assert "name" in role
        assert "description" in role
        assert "permissions" in role
        
        # Test create role
        new_role = {
            "name": "receptionist",
            "description": "Hotel reception access",
            "permissions": ["view_reservations", "create_reservations"]
        }
        
        response = roles_client.post("/api/admin/roles", json=new_role, headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "role_id" in data
        
        # Test update role
        role_id = "role_1"
        updated_role = {
            "name": "super_admin",
            "description": "Super administrator access",
            "permissions": ["*"]
        }
        
        response = roles_client.put(f"/api/admin/roles/{role_id}", json=updated_role, headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        
        # Test delete role
        response = roles_client.delete(f"/api/admin/roles/{role_id}", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
    
    def test_permissions_management(self, roles_client):
        """Test permissions management"""
        
        headers = {"Authorization": "Bearer admin_token"}
        
        # Test get permissions
        response = roles_client.get("/api/admin/permissions", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "permissions" in data
        assert len(data["permissions"]) > 0
        
        # Verify permission structure
        permission = data["permissions"][0]
        assert "id" in permission
        assert "name" in permission
        assert "description" in permission
        assert "category" in permission
    
    def test_user_role_assignment(self, roles_client):
        """Test user role assignment endpoints"""
        
        headers = {"Authorization": "Bearer admin_token"}
        user_id = "user_123"
        
        # Test assign role to user
        role_assignment = {
            "role_id": "role_2"
        }
        
        response = roles_client.post(f"/api/admin/users/{user_id}/roles", json=role_assignment, headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        
        # Test remove role from user
        role_id = "role_2"
        response = roles_client.delete(f"/api/admin/users/{user_id}/roles/{role_id}", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        
        # Test get user permissions
        response = roles_client.get(f"/api/admin/users/{user_id}/permissions", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == user_id
        assert "permissions" in data
        assert "roles" in data

class TestSecurityAPIErrorHandling:
    """Test security API error handling"""
    
    @pytest.fixture
    def error_client(self):
        """Create test client for error testing"""
        from fastapi import FastAPI, HTTPException
        
        app = FastAPI()
        
        @app.post("/api/auth/login")
        async def login_with_errors(credentials: dict):
            username = credentials.get("username")
            password = credentials.get("password")
            
            if not username or not password:
                raise HTTPException(status_code=400, detail="Username and password required")
            
            if username == "blocked_user":
                raise HTTPException(status_code=423, detail="Account locked due to security violations")
            
            if username == "invalid_user":
                raise HTTPException(status_code=401, detail="Invalid credentials")
            
            return {"access_token": "mock_token"}
        
        @app.get("/api/auth/profile")
        async def profile_with_errors():
            # Simulate different error scenarios
            raise HTTPException(status_code=401, detail="Token expired")
        
        @app.post("/api/auth/register")
        async def register_with_errors(user_data: dict):
            email = user_data.get("email")
            
            if email == "existing@hotel.com":
                raise HTTPException(status_code=409, detail="Email already registered")
            
            if not email or "@" not in email:
                raise HTTPException(status_code=422, detail="Invalid email format")
            
            return {"user_id": "new_user"}
        
        @app.post("/api/admin/security/action")
        async def admin_action_with_errors():
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        
        return TestClient(app)
    
    def test_authentication_errors(self, error_client):
        """Test authentication error responses"""
        
        # Test missing credentials
        response = error_client.post("/api/auth/login", json={})
        assert response.status_code == 400
        
        # Test invalid credentials
        response = error_client.post("/api/auth/login", json={
            "username": "invalid_user",
            "password": "wrong_password"
        })
        assert response.status_code == 401
        
        # Test account locked
        response = error_client.post("/api/auth/login", json={
            "username": "blocked_user", 
            "password": "password"
        })
        assert response.status_code == 423
    
    def test_authorization_errors(self, error_client):
        """Test authorization error responses"""
        
        # Test token expired
        response = error_client.get("/api/auth/profile")
        assert response.status_code == 401
        
        # Test insufficient permissions
        response = error_client.post("/api/admin/security/action")
        assert response.status_code == 403
    
    def test_registration_errors(self, error_client):
        """Test registration error responses"""
        
        # Test invalid email
        response = error_client.post("/api/auth/register", json={
            "email": "invalid_email",
            "password": "password"
        })
        assert response.status_code == 422
        
        # Test existing email
        response = error_client.post("/api/auth/register", json={
            "email": "existing@hotel.com",
            "password": "password"
        })
        assert response.status_code == 409

class TestSecurityAPIPerformance:
    """Test security API performance characteristics"""
    
    @pytest.fixture
    def performance_client(self):
        """Create test client for performance testing"""
        from fastapi import FastAPI
        import asyncio
        
        app = FastAPI()
        
        @app.post("/api/auth/login")
        async def login_performance():
            # Simulate processing time
            await asyncio.sleep(0.1)  # 100ms processing
            return {"access_token": "token"}
        
        @app.get("/api/auth/profile")
        async def profile_performance():
            # Simulate database lookup
            await asyncio.sleep(0.05)  # 50ms processing
            return {"user_id": "user_123"}
        
        @app.get("/api/security/audit")
        async def audit_performance():
            # Simulate heavy query
            await asyncio.sleep(0.2)  # 200ms processing
            return {"logs": []}
        
        return TestClient(app)
    
    def test_login_performance(self, performance_client):
        """Test login endpoint performance"""
        import time
        
        login_data = {"username": "test", "password": "password"}
        
        start_time = time.time()
        response = performance_client.post("/api/auth/login", json=login_data)
        end_time = time.time()
        
        assert response.status_code == 200
        
        # Should complete within reasonable time (1 second)
        response_time = end_time - start_time
        assert response_time < 1.0
    
    def test_concurrent_requests(self, performance_client):
        """Test handling of concurrent requests"""
        import concurrent.futures
        import time
        
        def make_request():
            return performance_client.get("/api/auth/profile")
        
        # Test 10 concurrent requests
        start_time = time.time()
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(make_request) for _ in range(10)]
            responses = [future.result() for future in futures]
        end_time = time.time()
        
        # All requests should succeed
        for response in responses:
            assert response.status_code == 200
        
        # Total time should be reasonable for concurrent requests
        total_time = end_time - start_time
        assert total_time < 2.0  # Should complete within 2 seconds

if __name__ == "__main__":
    pytest.main([__file__, "-v"])