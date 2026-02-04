import pytest
from fastapi.testclient import TestClient
from backend.server import app
from core.rate_limiter import rate_limiter
from core.two_factor import two_factor_auth
from core.validation import (
    UserRegistrationSchema,
    CourseCreateSchema,
    MessageSchema,
    sanitize_sql_input,
    validate_uuid
)
from core.security import generate_secure_token, hash_sensitive_data, verify_hash
import asyncio

client = TestClient(app)

class TestHealthCheck:
    def test_health_endpoint(self):
        response = client.get("/api/monitoring/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"

    def test_root_endpoint(self):
        response = client.get("/")
        assert response.status_code == 200
        assert "security" in response.json()
        assert response.json()["security"] == "enabled"

class TestInputValidation:
    def test_valid_user_registration(self):
        valid_data = {
            "username": "testuser123",
            "email": "test@example.com",
            "password": "Test123!@#Password",
            "full_name": "Test User"
        }
        schema = UserRegistrationSchema(**valid_data)
        assert schema.username == "testuser123"
        assert schema.email == "test@example.com"

    def test_invalid_username(self):
        with pytest.raises(ValueError):
            UserRegistrationSchema(
                username="test user!",
                email="test@example.com",
                password="Test123!@#Password"
            )

    def test_weak_password(self):
        with pytest.raises(ValueError):
            UserRegistrationSchema(
                username="testuser",
                email="test@example.com",
                password="weak"
            )

    def test_sql_injection_detection(self):
        with pytest.raises(ValueError):
            sanitize_sql_input("1' OR '1'='1")

        with pytest.raises(ValueError):
            sanitize_sql_input("DROP TABLE users;")

    def test_xss_sanitization(self):
        schema = MessageSchema(content="<script>alert('xss')</script>Hello")
        assert "<script>" not in schema.content

    def test_uuid_validation(self):
        valid_uuid = "123e4567-e89b-12d3-a456-426614174000"
        invalid_uuid = "not-a-uuid"

        assert validate_uuid(valid_uuid) == True
        assert validate_uuid(invalid_uuid) == False

class TestTwoFactorAuth:
    def test_generate_secret(self):
        secret = two_factor_auth.generate_secret()
        assert len(secret) == 32
        assert secret.isupper()

    def test_generate_qr_code(self):
        secret = two_factor_auth.generate_secret()
        qr_code = two_factor_auth.generate_qr_code("test@example.com", secret)
        assert qr_code.startswith("data:image/png;base64,")

    def test_verify_totp(self):
        secret = two_factor_auth.generate_secret()
        import pyotp
        totp = pyotp.TOTP(secret)
        token = totp.now()

        assert two_factor_auth.verify_totp(secret, token) == True
        assert two_factor_auth.verify_totp(secret, "000000") == False

    def test_generate_backup_codes(self):
        codes = two_factor_auth.generate_backup_codes(10)
        assert len(codes) == 10
        assert all(len(code.split('-')) == 3 for code in codes)

    def test_backup_code_hashing(self):
        code = "AB12-CD34-EF56"
        hashed = two_factor_auth.hash_backup_code(code)
        assert len(hashed) == 64
        assert hashed != code

class TestRateLimiting:
    @pytest.mark.asyncio
    async def test_rate_limit_enforcement(self):
        await rate_limiter.start()

        from fastapi import Request

        mock_request = type('MockRequest', (), {
            'headers': {},
            'client': type('Client', (), {'host': '127.0.0.1'})()
        })()

        for i in range(5):
            result = await rate_limiter.check_rate_limit(
                mock_request,
                max_requests=5,
                window_minutes=1
            )
            assert result == True

        with pytest.raises(Exception):
            await rate_limiter.check_rate_limit(
                mock_request,
                max_requests=5,
                window_minutes=1
            )

        await rate_limiter.stop()

    def test_rate_limit_tiers(self):
        admin_tier = rate_limiter.get_rate_limit_tier("admin")
        assert admin_tier == (10000, 1)

        user_tier = rate_limiter.get_rate_limit_tier("user")
        assert user_tier == (100, 1)

        anonymous_tier = rate_limiter.get_rate_limit_tier("anonymous")
        assert anonymous_tier == (20, 1)

class TestSecurity:
    def test_generate_secure_token(self):
        token1 = generate_secure_token()
        token2 = generate_secure_token()

        assert len(token1) > 0
        assert len(token2) > 0
        assert token1 != token2

    def test_hash_sensitive_data(self):
        data = "sensitive_info"
        hashed = hash_sensitive_data(data)

        assert len(hashed) == 64
        assert hashed != data

    def test_verify_hash(self):
        data = "test_data"
        hashed = hash_sensitive_data(data)

        assert verify_hash(data, hashed) == True
        assert verify_hash("wrong_data", hashed) == False

class TestValidationSchemas:
    def test_course_create_schema(self):
        valid_course = {
            "title": "Python Programming",
            "description": "Learn Python from scratch",
            "category": "Programming",
            "difficulty": "beginner",
            "duration_hours": 10,
            "price_tokens": 100
        }

        schema = CourseCreateSchema(**valid_course)
        assert schema.title == "Python Programming"
        assert schema.difficulty == "beginner"

    def test_course_invalid_difficulty(self):
        with pytest.raises(ValueError):
            CourseCreateSchema(
                title="Test Course",
                description="Test Description",
                category="Programming",
                difficulty="super_hard",
                duration_hours=10,
                price_tokens=100
            )

    def test_message_length_validation(self):
        with pytest.raises(ValueError):
            MessageSchema(content="a" * 10000)

class TestSecurityHeaders:
    def test_security_headers_present(self):
        response = client.get("/")

        assert "X-Content-Type-Options" in response.headers
        assert response.headers["X-Content-Type-Options"] == "nosniff"

        assert "X-Frame-Options" in response.headers
        assert response.headers["X-Frame-Options"] == "DENY"

        assert "Strict-Transport-Security" in response.headers

    def test_cors_headers(self):
        response = client.options("/")

        assert "access-control-allow-origin" in response.headers

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
