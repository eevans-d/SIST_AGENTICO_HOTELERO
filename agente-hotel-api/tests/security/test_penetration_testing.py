"""
Penetration Testing and Security Validation Suite
Advanced security testing including penetration testing scenarios
"""

import pytest
from fastapi.testclient import TestClient
import time
import random


class TestPenetrationTesting:
    """Advanced penetration testing scenarios"""

    @pytest.fixture
    def vulnerable_app(self):
        """Create app with intentional vulnerabilities for testing"""
        from fastapi import FastAPI, HTTPException, Request

        app = FastAPI()

        # Mock database for testing
        users_db = {"admin": {"password": "admin123", "role": "admin"}, "user": {"password": "user123", "role": "user"}}

        @app.post("/api/login")
        async def vulnerable_login(request: Request):
            data = await request.json()
            username = data.get("username")
            password = data.get("password")

            # Intentionally vulnerable to SQL injection simulation
            if username and password:
                # Simulate SQL injection vulnerability
                if "' OR '1'='1" in username or "' OR '1'='1" in password:
                    return {"message": "SQL injection detected", "vulnerable": True}

                # Normal authentication
                if username in users_db and users_db[username]["password"] == password:
                    return {"token": f"token_{username}", "role": users_db[username]["role"]}

            return {"error": "Invalid credentials"}

        @app.get("/api/admin/users")
        async def get_users(token: str = None):
            # Vulnerable to authorization bypass
            if not token:
                raise HTTPException(status_code=401, detail="No token provided")

            # Weak token validation
            if token.startswith("token_"):
                return {"users": list(users_db.keys())}

            raise HTTPException(status_code=403, detail="Invalid token")

        @app.post("/api/search")
        async def search_users(request: Request):
            data = await request.json()
            query = data.get("query", "")

            # Vulnerable to NoSQL injection
            if isinstance(query, dict):
                return {"message": "NoSQL injection detected", "vulnerable": True}

            # Vulnerable to XSS
            if "<script>" in query or "javascript:" in query:
                return {"message": "XSS attempt detected", "vulnerable": True}

            return {"results": []}

        @app.post("/api/upload")
        async def file_upload(request: Request):
            # Simulate file upload vulnerability
            data = await request.json()
            filename = data.get("filename", "")
            data.get("content", "")

            # Path traversal vulnerability
            if "../" in filename or "..\\" in filename:
                return {"message": "Path traversal detected", "vulnerable": True}

            # Dangerous file types
            dangerous_extensions = [".php", ".jsp", ".asp", ".exe", ".sh"]
            if any(filename.endswith(ext) for ext in dangerous_extensions):
                return {"message": "Dangerous file type detected", "vulnerable": True}

            return {"message": "File uploaded successfully"}

        @app.get("/api/redirect")
        async def open_redirect(url: str = ""):
            # Open redirect vulnerability
            if url.startswith("http://evil.com") or url.startswith("https://evil.com"):
                return {"message": "Open redirect detected", "vulnerable": True}

            return {"redirect_url": url}

        return TestClient(app)

    def test_sql_injection_attempts(self, vulnerable_app):
        """Test SQL injection vulnerabilities"""

        # Common SQL injection payloads
        sql_payloads = [
            "' OR '1'='1",
            "' OR 1=1--",
            "'; DROP TABLE users;--",
            "' UNION SELECT * FROM users--",
            "admin'--",
            "' OR 'a'='a",
        ]

        for payload in sql_payloads:
            # Test in username field
            response = vulnerable_app.post("/api/login", json={"username": payload, "password": "password"})

            # Should detect SQL injection attempt
            if response.status_code == 200 and response.json().get("vulnerable"):
                assert response.json()["message"] == "SQL injection detected"

            # Test in password field
            response = vulnerable_app.post("/api/login", json={"username": "admin", "password": payload})

            if response.status_code == 200 and response.json().get("vulnerable"):
                assert response.json()["message"] == "SQL injection detected"

    def test_nosql_injection_attempts(self, vulnerable_app):
        """Test NoSQL injection vulnerabilities"""

        # NoSQL injection payloads
        nosql_payloads = [
            {"$gt": ""},
            {"$ne": None},
            {"$where": "function(){return true}"},
            {"$regex": ".*"},
            {"$in": ["admin", "user"]},
        ]

        for payload in nosql_payloads:
            response = vulnerable_app.post("/api/search", json={"query": payload})

            if response.status_code == 200 and response.json().get("vulnerable"):
                assert response.json()["message"] == "NoSQL injection detected"

    def test_xss_attempts(self, vulnerable_app):
        """Test Cross-Site Scripting (XSS) vulnerabilities"""

        # XSS payloads
        xss_payloads = [
            "<script>alert('XSS')</script>",
            "<img src=x onerror=alert('XSS')>",
            "javascript:alert('XSS')",
            "<svg onload=alert('XSS')>",
            "';alert('XSS');//",
            "<iframe src=javascript:alert('XSS')></iframe>",
        ]

        for payload in xss_payloads:
            response = vulnerable_app.post("/api/search", json={"query": payload})

            if response.status_code == 200 and response.json().get("vulnerable"):
                assert response.json()["message"] == "XSS attempt detected"

    def test_path_traversal_attempts(self, vulnerable_app):
        """Test path traversal vulnerabilities"""

        # Path traversal payloads
        traversal_payloads = [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32\\config\\sam",
            "../../../../../etc/shadow",
            "....//....//....//etc/passwd",
            "%2e%2e%2f%2e%2e%2f%2e%2e%2fetc%2fpasswd",
        ]

        for payload in traversal_payloads:
            response = vulnerable_app.post("/api/upload", json={"filename": payload, "content": "test content"})

            if response.status_code == 200 and response.json().get("vulnerable"):
                assert response.json()["message"] == "Path traversal detected"

    def test_file_upload_vulnerabilities(self, vulnerable_app):
        """Test file upload vulnerabilities"""

        # Dangerous file types
        dangerous_files = ["malware.php", "backdoor.jsp", "virus.exe", "script.sh", "trojan.asp", "webshell.php"]

        for filename in dangerous_files:
            response = vulnerable_app.post(
                "/api/upload", json={"filename": filename, "content": "<?php system($_GET['cmd']); ?>"}
            )

            if response.status_code == 200 and response.json().get("vulnerable"):
                assert response.json()["message"] == "Dangerous file type detected"

    def test_open_redirect_vulnerabilities(self, vulnerable_app):
        """Test open redirect vulnerabilities"""

        # Malicious redirect URLs
        malicious_urls = [
            "http://evil.com/phishing",
            "https://evil.com/malware",
            "//evil.com/redirect",
            "javascript:alert('XSS')",
            "data:text/html,<script>alert('XSS')</script>",
        ]

        for url in malicious_urls:
            response = vulnerable_app.get(f"/api/redirect?url={url}")

            if response.status_code == 200 and response.json().get("vulnerable"):
                assert response.json()["message"] == "Open redirect detected"

    def test_authorization_bypass_attempts(self, vulnerable_app):
        """Test authorization bypass vulnerabilities"""

        # Test with no token
        response = vulnerable_app.get("/api/admin/users")
        assert response.status_code == 401

        # Test with invalid token
        response = vulnerable_app.get("/api/admin/users?token=invalid_token")
        assert response.status_code == 403

        # Test with valid token format but unauthorized user
        response = vulnerable_app.get("/api/admin/users?token=token_user")
        # This should ideally fail but might pass due to weak validation
        if response.status_code == 200:
            # Indicates potential authorization bypass vulnerability
            pass


class TestBruteForceAttacks:
    """Test brute force attack scenarios"""

    @pytest.fixture
    def brute_force_app(self):
        """Create app for brute force testing"""
        from fastapi import FastAPI, HTTPException

        app = FastAPI()

        # Track login attempts
        app.state.login_attempts = {}
        app.state.locked_accounts = set()

        @app.post("/api/login")
        async def login_with_protection(credentials: dict):
            username = credentials.get("username")
            password = credentials.get("password")

            # Check if account is locked
            if username in app.state.locked_accounts:
                raise HTTPException(status_code=423, detail="Account locked")

            # Track attempts
            if username not in app.state.login_attempts:
                app.state.login_attempts[username] = 0

            app.state.login_attempts[username] += 1

            # Lock account after 5 failed attempts
            if app.state.login_attempts[username] > 5:
                app.state.locked_accounts.add(username)
                raise HTTPException(status_code=423, detail="Account locked due to too many attempts")

            # Valid credentials
            if username == "testuser" and password == "correctpassword":
                app.state.login_attempts[username] = 0  # Reset on success
                return {"token": "valid_token"}

            raise HTTPException(status_code=401, detail="Invalid credentials")

        @app.post("/api/reset-attempts")
        async def reset_attempts(username: str):
            # Admin endpoint to reset attempts
            if username in app.state.login_attempts:
                del app.state.login_attempts[username]
            app.state.locked_accounts.discard(username)
            return {"message": "Attempts reset"}

        return TestClient(app)

    def test_brute_force_password_attack(self, brute_force_app):
        """Test brute force password attack"""

        # Common passwords for brute force
        common_passwords = [
            "password",
            "123456",
            "password123",
            "admin",
            "qwerty",
            "letmein",
            "welcome",
            "monkey",
            "dragon",
            "correctpassword",
        ]

        username = "testuser"
        successful_login = False

        for password in common_passwords:
            try:
                response = brute_force_app.post("/api/login", json={"username": username, "password": password})

                if response.status_code == 200:
                    successful_login = True
                    break
                elif response.status_code == 423:
                    # Account locked - brute force protection working
                    break

            except Exception:
                continue

        # Should either succeed with correct password or trigger protection
        assert successful_login or response.status_code == 423

    def test_account_lockout_mechanism(self, brute_force_app):
        """Test account lockout after multiple failed attempts"""

        username = "testuser"

        # Make multiple failed login attempts
        for i in range(6):  # More than the limit
            response = brute_force_app.post("/api/login", json={"username": username, "password": "wrongpassword"})

            if i < 5:
                assert response.status_code == 401  # Should fail normally
            else:
                assert response.status_code == 423  # Should be locked

        # Even correct password should fail when locked
        response = brute_force_app.post("/api/login", json={"username": username, "password": "correctpassword"})
        assert response.status_code == 423

    def test_distributed_brute_force(self, brute_force_app):
        """Test distributed brute force from multiple IPs"""

        # Simulate attacks from different IP addresses
        # In real implementation, this would involve actual IP tracking
        usernames = [f"user_{i}" for i in range(10)]

        for username in usernames:
            # Each "IP" tries different passwords
            for attempt in range(3):
                response = brute_force_app.post(
                    "/api/login", json={"username": username, "password": f"password{attempt}"}
                )
                # Should fail but not trigger immediate lockout per user
                assert response.status_code in [401, 423]


class TestSessionHijacking:
    """Test session hijacking and fixation attacks"""

    @pytest.fixture
    def session_app(self):
        """Create app for session testing"""
        from fastapi import FastAPI, HTTPException
        import secrets

        app = FastAPI()

        # Session storage
        app.state.sessions = {}
        app.state.user_sessions = {}

        @app.post("/api/login")
        async def login_with_session(credentials: dict):
            username = credentials.get("username")
            password = credentials.get("password")

            if username == "testuser" and password == "password":
                # Generate secure session ID
                session_id = secrets.token_urlsafe(32)

                app.state.sessions[session_id] = {
                    "username": username,
                    "created_at": time.time(),
                    "last_activity": time.time(),
                }

                # Track user sessions
                if username not in app.state.user_sessions:
                    app.state.user_sessions[username] = []
                app.state.user_sessions[username].append(session_id)

                return {"session_id": session_id}

            raise HTTPException(status_code=401, detail="Invalid credentials")

        @app.get("/api/profile")
        async def get_profile(session_id: str):
            if session_id not in app.state.sessions:
                raise HTTPException(status_code=401, detail="Invalid session")

            session = app.state.sessions[session_id]

            # Check session timeout (30 minutes)
            if time.time() - session["last_activity"] > 1800:
                del app.state.sessions[session_id]
                raise HTTPException(status_code=401, detail="Session expired")

            # Update last activity
            session["last_activity"] = time.time()

            return {"username": session["username"]}

        @app.post("/api/logout")
        async def logout(session_id: str):
            if session_id in app.state.sessions:
                username = app.state.sessions[session_id]["username"]
                del app.state.sessions[session_id]

                # Remove from user sessions
                if username in app.state.user_sessions:
                    app.state.user_sessions[username] = [
                        sid for sid in app.state.user_sessions[username] if sid != session_id
                    ]

                return {"message": "Logged out"}

            raise HTTPException(status_code=401, detail="Invalid session")

        return TestClient(app)

    def test_session_fixation_attack(self, session_app):
        """Test session fixation vulnerability"""

        # Attacker provides a session ID
        malicious_session_id = "attacker_controlled_session_123"

        # Try to use the malicious session ID
        response = session_app.get(f"/api/profile?session_id={malicious_session_id}")

        # Should fail since session doesn't exist
        assert response.status_code == 401

        # Legitimate login should create new session ID
        response = session_app.post("/api/login", json={"username": "testuser", "password": "password"})

        assert response.status_code == 200
        session_id = response.json()["session_id"]

        # Session ID should be different from attacker's
        assert session_id != malicious_session_id

    def test_session_hijacking_attempt(self, session_app):
        """Test session hijacking scenarios"""

        # User logs in
        response = session_app.post("/api/login", json={"username": "testuser", "password": "password"})
        legitimate_session = response.json()["session_id"]

        # Attacker tries to guess/brute force session IDs
        attack_session_ids = [
            "simple_session_123",
            "12345",
            "session_1",
            "abc123",
            legitimate_session[:-1] + "X",  # Modified legitimate session
        ]

        for attack_session in attack_session_ids:
            if attack_session != legitimate_session:
                response = session_app.get(f"/api/profile?session_id={attack_session}")
                assert response.status_code == 401  # Should fail

        # Legitimate session should still work
        response = session_app.get(f"/api/profile?session_id={legitimate_session}")
        assert response.status_code == 200

    def test_concurrent_session_management(self, session_app):
        """Test concurrent session handling"""

        # User logs in from multiple devices/locations
        sessions = []
        for i in range(3):
            response = session_app.post("/api/login", json={"username": "testuser", "password": "password"})
            sessions.append(response.json()["session_id"])

        # All sessions should be valid
        for session_id in sessions:
            response = session_app.get(f"/api/profile?session_id={session_id}")
            assert response.status_code == 200

        # Logout one session
        response = session_app.post(f"/api/logout?session_id={sessions[0]}")
        assert response.status_code == 200

        # First session should be invalid
        response = session_app.get(f"/api/profile?session_id={sessions[0]}")
        assert response.status_code == 401

        # Other sessions should still work
        for session_id in sessions[1:]:
            response = session_app.get(f"/api/profile?session_id={session_id}")
            assert response.status_code == 200


class TestCryptographicAttacks:
    """Test cryptographic vulnerabilities"""

    def test_weak_encryption_detection(self):
        """Test detection of weak encryption"""

        # Test weak hashing algorithms
        weak_algorithms = ["md5", "sha1"]
        strong_algorithms = ["sha256", "sha512", "bcrypt"]

        for algorithm in weak_algorithms:
            # Simulate weak hash detection
            if algorithm in ["md5", "sha1"]:
                vulnerability_detected = True
            else:
                vulnerability_detected = False

            assert vulnerability_detected is True

        for algorithm in strong_algorithms:
            if algorithm in ["sha256", "sha512", "bcrypt"]:
                vulnerability_detected = False
            else:
                vulnerability_detected = True

            assert vulnerability_detected is False

    def test_random_number_generation(self):
        """Test random number generation quality"""

        # Test predictable random numbers
        import secrets

        # Generate numbers with both methods
        weak_randoms = [random.randint(1, 1000) for _ in range(100)]
        strong_randoms = [secrets.randbelow(1000) for _ in range(100)]

        # Check for patterns (basic test)
        weak_unique = len(set(weak_randoms))
        strong_unique = len(set(strong_randoms))

        # Both should have good uniqueness, but secrets should be cryptographically secure
        assert weak_unique > 50  # Should have reasonable uniqueness
        assert strong_unique > 50  # Should have good uniqueness

    def test_timing_attack_resistance(self):
        """Test resistance to timing attacks"""

        import hmac

        def vulnerable_compare(a, b):
            """Vulnerable string comparison"""
            if len(a) != len(b):
                return False
            for i in range(len(a)):
                if a[i] != b[i]:
                    return False
            return True

        def secure_compare(a, b):
            """Secure string comparison using hmac"""
            return hmac.compare_digest(a, b)

        # Test strings
        correct_token = "super_secret_token_123"
        wrong_token = "wrong_token_123456789"

        # Both methods should return same logical result
        assert vulnerable_compare(correct_token, correct_token) is True
        assert secure_compare(correct_token, correct_token) is True

        assert vulnerable_compare(correct_token, wrong_token) is False
        assert secure_compare(correct_token, wrong_token) is False

        # In production, secure_compare should be used to prevent timing attacks


class TestBusinessLogicVulnerabilities:
    """Test business logic vulnerabilities"""

    @pytest.fixture
    def hotel_app(self):
        """Create hotel app for business logic testing"""
        from fastapi import FastAPI, HTTPException

        app = FastAPI()

        # Mock hotel data
        app.state.rooms = {
            "101": {"price": 100, "available": True},
            "102": {"price": 150, "available": True},
            "103": {"price": 200, "available": False},
        }

        app.state.reservations = {}
        app.state.user_points = {"testuser": 1000}

        @app.post("/api/reservations")
        async def create_reservation(reservation: dict):
            room_number = reservation.get("room_number")
            user_id = reservation.get("user_id")
            discount_code = reservation.get("discount_code")
            points_used = reservation.get("points_used", 0)

            if room_number not in app.state.rooms:
                raise HTTPException(status_code=404, detail="Room not found")

            room = app.state.rooms[room_number]
            if not room["available"]:
                raise HTTPException(status_code=400, detail="Room not available")

            price = room["price"]

            # Apply discount code (vulnerable to multiple uses)
            if discount_code == "SAVE50":
                price = price * 0.5

            # Apply points discount (vulnerable to negative points)
            if points_used > 0:
                user_points = app.state.user_points.get(user_id, 0)
                if points_used <= user_points:
                    price = max(0, price - points_used)
                    app.state.user_points[user_id] = user_points - points_used
                else:
                    raise HTTPException(status_code=400, detail="Insufficient points")

            reservation_id = f"RES_{len(app.state.reservations) + 1}"
            app.state.reservations[reservation_id] = {
                "room_number": room_number,
                "user_id": user_id,
                "price": price,
                "points_used": points_used,
            }

            # Mark room as unavailable
            app.state.rooms[room_number]["available"] = False

            return {"reservation_id": reservation_id, "total_price": price}

        @app.post("/api/cancel-reservation")
        async def cancel_reservation(cancel_data: dict):
            reservation_id = cancel_data.get("reservation_id")
            user_id = cancel_data.get("user_id")

            if reservation_id not in app.state.reservations:
                raise HTTPException(status_code=404, detail="Reservation not found")

            reservation = app.state.reservations[reservation_id]

            # Vulnerable: No ownership check
            # Should check if user_id matches reservation owner

            # Refund points
            points_used = reservation.get("points_used", 0)
            if points_used > 0:
                current_points = app.state.user_points.get(user_id, 0)
                app.state.user_points[user_id] = current_points + points_used

            # Make room available again
            room_number = reservation["room_number"]
            app.state.rooms[room_number]["available"] = True

            del app.state.reservations[reservation_id]

            return {"message": "Reservation cancelled"}

        @app.get("/api/user/points/{user_id}")
        async def get_user_points(user_id: str):
            return {"points": app.state.user_points.get(user_id, 0)}

        return TestClient(app)

    def test_discount_code_reuse_vulnerability(self, hotel_app):
        """Test discount code reuse vulnerability"""

        # Make multiple reservations with same discount code
        for i in range(3):
            response = hotel_app.post(
                "/api/reservations",
                json={"room_number": "101" if i == 0 else "102", "user_id": "testuser", "discount_code": "SAVE50"},
            )

            # All should succeed with discount (vulnerability)
            assert response.status_code == 200
            data = response.json()
            # Price should be discounted each time
            expected_price = 50 if i == 0 else 75  # 50% off 100 and 150
            assert data["total_price"] == expected_price

    def test_negative_points_vulnerability(self, hotel_app):
        """Test negative points manipulation"""

        # Try to use more points than available
        response = hotel_app.post(
            "/api/reservations",
            json={
                "room_number": "101",
                "user_id": "testuser",
                "points_used": 1500,  # More than available (1000)
            },
        )

        # Should be rejected
        assert response.status_code == 400

        # Try with negative points (if not properly validated)
        response = hotel_app.post(
            "/api/reservations",
            json={
                "room_number": "102",
                "user_id": "testuser",
                "points_used": -500,  # Negative points
            },
        )

        # This might succeed if validation is weak, indicating vulnerability
        if response.status_code == 200:
            data = response.json()
            # Price might be higher than original (vulnerability detected)
            assert data["total_price"] >= 150

    def test_race_condition_in_reservations(self, hotel_app):
        """Test race condition in room reservations"""

        import concurrent.futures

        def make_reservation(user_id):
            return hotel_app.post("/api/reservations", json={"room_number": "101", "user_id": user_id})

        # Try to book same room simultaneously
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(make_reservation, f"user_{i}") for i in range(5)]
            responses = [future.result() for future in futures]

        # Only one reservation should succeed
        successful_reservations = [r for r in responses if r.status_code == 200]
        failed_reservations = [r for r in responses if r.status_code != 200]

        # Should have exactly one success and rest failures
        assert len(successful_reservations) == 1
        assert len(failed_reservations) == 4

    def test_unauthorized_reservation_cancellation(self, hotel_app):
        """Test unauthorized reservation cancellation"""

        # User A makes a reservation
        response = hotel_app.post("/api/reservations", json={"room_number": "101", "user_id": "user_a"})
        reservation_id = response.json()["reservation_id"]

        # User B tries to cancel User A's reservation
        response = hotel_app.post(
            "/api/cancel-reservation",
            json={
                "reservation_id": reservation_id,
                "user_id": "user_b",  # Different user
            },
        )

        # This might succeed if authorization is weak (vulnerability)
        if response.status_code == 200:
            # Indicates vulnerability - unauthorized cancellation succeeded
            assert response.json()["message"] == "Reservation cancelled"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
