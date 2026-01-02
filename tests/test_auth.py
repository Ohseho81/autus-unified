# tests/test_auth.py
# 인증 모듈 테스트

import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from fastapi.testclient import TestClient
from auth.middleware import (
    create_jwt_token,
    decode_jwt_token,
    validate_api_key,
    generate_api_key,
    RateLimiter
)
from main import app

client = TestClient(app)


class TestJWTToken:
    """JWT 토큰 테스트"""
    
    def test_create_token(self):
        """토큰 생성"""
        token = create_jwt_token("user_123", ["read", "write"])
        
        assert token is not None
        assert len(token) > 50
    
    def test_decode_valid_token(self):
        """유효한 토큰 디코드"""
        token = create_jwt_token("user_456", ["read"])
        payload = decode_jwt_token(token)
        
        assert payload is not None
        assert payload.sub == "user_456"
        assert "read" in payload.scopes
    
    def test_decode_invalid_token(self):
        """잘못된 토큰"""
        payload = decode_jwt_token("invalid_token")
        assert payload is None
    
    def test_token_contains_scopes(self):
        """토큰에 스코프 포함"""
        token = create_jwt_token("user", ["read", "write", "admin"])
        payload = decode_jwt_token(token)
        
        assert "read" in payload.scopes
        assert "write" in payload.scopes
        assert "admin" in payload.scopes


class TestAPIKey:
    """API Key 테스트"""
    
    def test_validate_dev_key(self):
        """개발 키 검증"""
        info = validate_api_key("autus_dev_key_123")
        
        assert info is not None
        assert info.client_id == "development"
        assert "admin" in info.scopes
    
    def test_validate_test_key(self):
        """테스트 키 검증"""
        info = validate_api_key("autus_test_key_456")
        
        assert info is not None
        assert info.client_id == "testing"
        assert "read" in info.scopes
        assert "write" in info.scopes
    
    def test_validate_invalid_key(self):
        """잘못된 키"""
        info = validate_api_key("invalid_key")
        assert info is None
    
    def test_generate_new_key(self):
        """새 키 생성"""
        key = generate_api_key("new_client", ["read"])
        
        assert key.startswith("autus_")
        assert len(key) > 20
        
        # 생성된 키 검증
        info = validate_api_key(key)
        assert info is not None
        assert info.client_id == "new_client"


class TestRateLimiter:
    """Rate Limiter 테스트"""
    
    def test_allows_initial_request(self):
        """초기 요청 허용"""
        limiter = RateLimiter(max_requests=10, window_seconds=60)
        
        assert limiter.is_allowed("client_1") is True
    
    def test_allows_up_to_limit(self):
        """제한까지 허용"""
        limiter = RateLimiter(max_requests=5, window_seconds=60)
        
        for i in range(5):
            assert limiter.is_allowed("client_2") is True
    
    def test_blocks_over_limit(self):
        """제한 초과 차단"""
        limiter = RateLimiter(max_requests=3, window_seconds=60)
        
        for _ in range(3):
            limiter.is_allowed("client_3")
        
        assert limiter.is_allowed("client_3") is False
    
    def test_remaining_count(self):
        """남은 요청 수"""
        limiter = RateLimiter(max_requests=10, window_seconds=60)
        
        for _ in range(3):
            limiter.is_allowed("client_4")
        
        assert limiter.get_remaining("client_4") == 7
    
    def test_different_clients_independent(self):
        """클라이언트별 독립"""
        limiter = RateLimiter(max_requests=2, window_seconds=60)
        
        limiter.is_allowed("client_a")
        limiter.is_allowed("client_a")
        
        # client_a는 제한 도달
        assert limiter.is_allowed("client_a") is False
        
        # client_b는 아직 가능
        assert limiter.is_allowed("client_b") is True


class TestAuthAPI:
    """Auth API 테스트"""
    
    def test_login_success(self):
        """로그인 성공"""
        response = client.post("/auth/login", json={
            "username": "admin",
            "password": "admin123"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
    
    def test_login_invalid_credentials(self):
        """잘못된 인증"""
        response = client.post("/auth/login", json={
            "username": "admin",
            "password": "wrong_password"
        })
        
        assert response.status_code == 401
    
    def test_login_unknown_user(self):
        """존재하지 않는 사용자"""
        response = client.post("/auth/login", json={
            "username": "unknown",
            "password": "password"
        })
        
        assert response.status_code == 401
    
    def test_me_with_jwt(self):
        """JWT로 /me 접근"""
        # 로그인
        login_response = client.post("/auth/login", json={
            "username": "user",
            "password": "user123"
        })
        token = login_response.json()["access_token"]
        
        # /me 접근
        response = client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["authenticated"] is True
        assert data["user_id"] == "user"
    
    def test_me_with_api_key(self):
        """API Key로 /me 접근"""
        response = client.get(
            "/auth/me",
            headers={"X-API-Key": "autus_dev_key_123"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["authenticated"] is True
        assert data["client_id"] == "development"
    
    def test_me_without_auth(self):
        """인증 없이 /me 접근"""
        response = client.get("/auth/me")
        
        assert response.status_code == 401
    
    def test_rate_limit_endpoint(self):
        """Rate Limit 상태 확인"""
        response = client.get(
            "/auth/rate-limit",
            headers={"X-API-Key": "autus_dev_key_123"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "limit" in data
        assert "remaining" in data
    
    def test_create_api_key_requires_admin(self):
        """API Key 생성은 admin 필요"""
        # user 권한으로 시도
        login_response = client.post("/auth/login", json={
            "username": "user",
            "password": "user123"
        })
        token = login_response.json()["access_token"]
        
        response = client.post(
            "/auth/api-key",
            json={"client_name": "test_client"},
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 403  # Forbidden
    
    def test_create_api_key_as_admin(self):
        """admin으로 API Key 생성"""
        login_response = client.post("/auth/login", json={
            "username": "admin",
            "password": "admin123"
        })
        token = login_response.json()["access_token"]
        
        response = client.post(
            "/auth/api-key",
            json={"client_name": "new_client", "scopes": ["read"]},
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "api_key" in data
        assert data["client_name"] == "new_client"
    
    def test_refresh_token(self):
        """토큰 갱신"""
        login_response = client.post("/auth/login", json={
            "username": "user",
            "password": "user123"
        })
        token = login_response.json()["access_token"]
        
        response = client.post(
            "/auth/refresh",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["access_token"] != token  # 새 토큰

# tests/test_auth.py
# 인증 모듈 테스트

import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from fastapi.testclient import TestClient
from auth.middleware import (
    create_jwt_token,
    decode_jwt_token,
    validate_api_key,
    generate_api_key,
    RateLimiter
)
from main import app

client = TestClient(app)


class TestJWTToken:
    """JWT 토큰 테스트"""
    
    def test_create_token(self):
        """토큰 생성"""
        token = create_jwt_token("user_123", ["read", "write"])
        
        assert token is not None
        assert len(token) > 50
    
    def test_decode_valid_token(self):
        """유효한 토큰 디코드"""
        token = create_jwt_token("user_456", ["read"])
        payload = decode_jwt_token(token)
        
        assert payload is not None
        assert payload.sub == "user_456"
        assert "read" in payload.scopes
    
    def test_decode_invalid_token(self):
        """잘못된 토큰"""
        payload = decode_jwt_token("invalid_token")
        assert payload is None
    
    def test_token_contains_scopes(self):
        """토큰에 스코프 포함"""
        token = create_jwt_token("user", ["read", "write", "admin"])
        payload = decode_jwt_token(token)
        
        assert "read" in payload.scopes
        assert "write" in payload.scopes
        assert "admin" in payload.scopes


class TestAPIKey:
    """API Key 테스트"""
    
    def test_validate_dev_key(self):
        """개발 키 검증"""
        info = validate_api_key("autus_dev_key_123")
        
        assert info is not None
        assert info.client_id == "development"
        assert "admin" in info.scopes
    
    def test_validate_test_key(self):
        """테스트 키 검증"""
        info = validate_api_key("autus_test_key_456")
        
        assert info is not None
        assert info.client_id == "testing"
        assert "read" in info.scopes
        assert "write" in info.scopes
    
    def test_validate_invalid_key(self):
        """잘못된 키"""
        info = validate_api_key("invalid_key")
        assert info is None
    
    def test_generate_new_key(self):
        """새 키 생성"""
        key = generate_api_key("new_client", ["read"])
        
        assert key.startswith("autus_")
        assert len(key) > 20
        
        # 생성된 키 검증
        info = validate_api_key(key)
        assert info is not None
        assert info.client_id == "new_client"


class TestRateLimiter:
    """Rate Limiter 테스트"""
    
    def test_allows_initial_request(self):
        """초기 요청 허용"""
        limiter = RateLimiter(max_requests=10, window_seconds=60)
        
        assert limiter.is_allowed("client_1") is True
    
    def test_allows_up_to_limit(self):
        """제한까지 허용"""
        limiter = RateLimiter(max_requests=5, window_seconds=60)
        
        for i in range(5):
            assert limiter.is_allowed("client_2") is True
    
    def test_blocks_over_limit(self):
        """제한 초과 차단"""
        limiter = RateLimiter(max_requests=3, window_seconds=60)
        
        for _ in range(3):
            limiter.is_allowed("client_3")
        
        assert limiter.is_allowed("client_3") is False
    
    def test_remaining_count(self):
        """남은 요청 수"""
        limiter = RateLimiter(max_requests=10, window_seconds=60)
        
        for _ in range(3):
            limiter.is_allowed("client_4")
        
        assert limiter.get_remaining("client_4") == 7
    
    def test_different_clients_independent(self):
        """클라이언트별 독립"""
        limiter = RateLimiter(max_requests=2, window_seconds=60)
        
        limiter.is_allowed("client_a")
        limiter.is_allowed("client_a")
        
        # client_a는 제한 도달
        assert limiter.is_allowed("client_a") is False
        
        # client_b는 아직 가능
        assert limiter.is_allowed("client_b") is True


class TestAuthAPI:
    """Auth API 테스트"""
    
    def test_login_success(self):
        """로그인 성공"""
        response = client.post("/auth/login", json={
            "username": "admin",
            "password": "admin123"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
    
    def test_login_invalid_credentials(self):
        """잘못된 인증"""
        response = client.post("/auth/login", json={
            "username": "admin",
            "password": "wrong_password"
        })
        
        assert response.status_code == 401
    
    def test_login_unknown_user(self):
        """존재하지 않는 사용자"""
        response = client.post("/auth/login", json={
            "username": "unknown",
            "password": "password"
        })
        
        assert response.status_code == 401
    
    def test_me_with_jwt(self):
        """JWT로 /me 접근"""
        # 로그인
        login_response = client.post("/auth/login", json={
            "username": "user",
            "password": "user123"
        })
        token = login_response.json()["access_token"]
        
        # /me 접근
        response = client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["authenticated"] is True
        assert data["user_id"] == "user"
    
    def test_me_with_api_key(self):
        """API Key로 /me 접근"""
        response = client.get(
            "/auth/me",
            headers={"X-API-Key": "autus_dev_key_123"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["authenticated"] is True
        assert data["client_id"] == "development"
    
    def test_me_without_auth(self):
        """인증 없이 /me 접근"""
        response = client.get("/auth/me")
        
        assert response.status_code == 401
    
    def test_rate_limit_endpoint(self):
        """Rate Limit 상태 확인"""
        response = client.get(
            "/auth/rate-limit",
            headers={"X-API-Key": "autus_dev_key_123"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "limit" in data
        assert "remaining" in data
    
    def test_create_api_key_requires_admin(self):
        """API Key 생성은 admin 필요"""
        # user 권한으로 시도
        login_response = client.post("/auth/login", json={
            "username": "user",
            "password": "user123"
        })
        token = login_response.json()["access_token"]
        
        response = client.post(
            "/auth/api-key",
            json={"client_name": "test_client"},
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 403  # Forbidden
    
    def test_create_api_key_as_admin(self):
        """admin으로 API Key 생성"""
        login_response = client.post("/auth/login", json={
            "username": "admin",
            "password": "admin123"
        })
        token = login_response.json()["access_token"]
        
        response = client.post(
            "/auth/api-key",
            json={"client_name": "new_client", "scopes": ["read"]},
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "api_key" in data
        assert data["client_name"] == "new_client"
    
    def test_refresh_token(self):
        """토큰 갱신"""
        login_response = client.post("/auth/login", json={
            "username": "user",
            "password": "user123"
        })
        token = login_response.json()["access_token"]
        
        response = client.post(
            "/auth/refresh",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["access_token"] != token  # 새 토큰


