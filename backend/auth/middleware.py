# backend/auth/middleware.py
# API 인증 미들웨어

import os
import time
import hashlib
import hmac
from typing import Optional, Callable
from datetime import datetime, timedelta

from fastapi import Request, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials, APIKeyHeader
import jwt
from pydantic import BaseModel


# 환경 변수
SECRET_KEY = os.getenv("AUTUS_SECRET_KEY", "autus_dev_secret_key_change_in_production")
API_KEY_HEADER = "X-API-Key"
JWT_ALGORITHM = "HS256"
JWT_EXPIRY_HOURS = 24


# Security schemes
bearer_scheme = HTTPBearer(auto_error=False)
api_key_header = APIKeyHeader(name=API_KEY_HEADER, auto_error=False)


class TokenPayload(BaseModel):
    """JWT 페이로드"""
    sub: str  # subject (user_id)
    exp: int  # expiry timestamp
    iat: int  # issued at
    scopes: list[str] = []


class APIKeyInfo(BaseModel):
    """API Key 정보"""
    key_id: str
    client_id: str
    scopes: list[str]
    created_at: datetime
    expires_at: Optional[datetime] = None


# In-memory API keys (프로덕션에서는 DB 사용)
API_KEYS = {
    "autus_dev_key_123": APIKeyInfo(
        key_id="dev_001",
        client_id="development",
        scopes=["read", "write", "admin"],
        created_at=datetime.now()
    ),
    "autus_test_key_456": APIKeyInfo(
        key_id="test_001",
        client_id="testing",
        scopes=["read", "write"],
        created_at=datetime.now()
    )
}


def create_jwt_token(user_id: str, scopes: list[str] = None) -> str:
    """JWT 토큰 생성"""
    now = datetime.utcnow()
    payload = {
        "sub": user_id,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(hours=JWT_EXPIRY_HOURS)).timestamp()),
        "scopes": scopes or []
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=JWT_ALGORITHM)


def decode_jwt_token(token: str) -> Optional[TokenPayload]:
    """JWT 토큰 디코드"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[JWT_ALGORITHM])
        return TokenPayload(**payload)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        return None


def validate_api_key(api_key: str) -> Optional[APIKeyInfo]:
    """API Key 검증"""
    return API_KEYS.get(api_key)


def generate_api_key(client_id: str, scopes: list[str] = None) -> str:
    """새 API Key 생성"""
    timestamp = str(time.time())
    raw = f"{client_id}:{timestamp}:{SECRET_KEY}"
    key = f"autus_{hashlib.sha256(raw.encode()).hexdigest()[:32]}"
    
    API_KEYS[key] = APIKeyInfo(
        key_id=f"key_{len(API_KEYS) + 1}",
        client_id=client_id,
        scopes=scopes or ["read"],
        created_at=datetime.now()
    )
    
    return key


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    api_key: str = Depends(api_key_header)
) -> Optional[dict]:
    """
    현재 사용자 가져오기
    
    인증 우선순위:
    1. Bearer Token (JWT)
    2. API Key (X-API-Key header)
    """
    # 1. JWT 토큰 확인
    if credentials:
        token_data = decode_jwt_token(credentials.credentials)
        if token_data:
            return {
                "type": "jwt",
                "user_id": token_data.sub,
                "scopes": token_data.scopes
            }
    
    # 2. API Key 확인
    if api_key:
        key_info = validate_api_key(api_key)
        if key_info:
            return {
                "type": "api_key",
                "client_id": key_info.client_id,
                "scopes": key_info.scopes
            }
    
    return None


async def require_auth(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    api_key: str = Depends(api_key_header)
) -> dict:
    """인증 필수"""
    user = await get_current_user(credentials, api_key)
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"}
        )
    return user


def require_scope(required_scope: str):
    """특정 스코프 필수"""
    async def scope_checker(user: dict = Depends(require_auth)) -> dict:
        if required_scope not in user.get("scopes", []):
            raise HTTPException(
                status_code=403,
                detail=f"Scope '{required_scope}' required"
            )
        return user
    return scope_checker


async def optional_auth(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    api_key: str = Depends(api_key_header)
) -> Optional[dict]:
    """인증 선택적"""
    return await get_current_user(credentials, api_key)


# Rate Limiting
class RateLimiter:
    """요청 제한"""
    
    def __init__(self, max_requests: int = 100, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests = {}  # {client_id: [(timestamp, count)]}
    
    def _clean_old_requests(self, client_id: str):
        """오래된 요청 정리"""
        cutoff = time.time() - self.window_seconds
        if client_id in self.requests:
            self.requests[client_id] = [
                (ts, count) for ts, count in self.requests[client_id]
                if ts > cutoff
            ]
    
    def is_allowed(self, client_id: str) -> bool:
        """요청 허용 여부"""
        self._clean_old_requests(client_id)
        
        if client_id not in self.requests:
            self.requests[client_id] = []
        
        total = sum(count for _, count in self.requests[client_id])
        
        if total >= self.max_requests:
            return False
        
        self.requests[client_id].append((time.time(), 1))
        return True
    
    def get_remaining(self, client_id: str) -> int:
        """남은 요청 수"""
        self._clean_old_requests(client_id)
        total = sum(count for _, count in self.requests.get(client_id, []))
        return max(0, self.max_requests - total)


# 글로벌 Rate Limiter
rate_limiter = RateLimiter(max_requests=100, window_seconds=60)


def check_rate_limit(client_id: str = "anonymous"):
    """Rate Limit 체크 의존성"""
    async def checker(user: dict = Depends(optional_auth)) -> None:
        cid = user.get("client_id") or user.get("user_id") if user else client_id
        
        if not rate_limiter.is_allowed(cid):
            remaining = rate_limiter.get_remaining(cid)
            raise HTTPException(
                status_code=429,
                detail="Too many requests",
                headers={
                    "X-RateLimit-Remaining": str(remaining),
                    "X-RateLimit-Reset": str(rate_limiter.window_seconds)
                }
            )
    return checker

# backend/auth/middleware.py
# API 인증 미들웨어

import os
import time
import hashlib
import hmac
from typing import Optional, Callable
from datetime import datetime, timedelta

from fastapi import Request, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials, APIKeyHeader
import jwt
from pydantic import BaseModel


# 환경 변수
SECRET_KEY = os.getenv("AUTUS_SECRET_KEY", "autus_dev_secret_key_change_in_production")
API_KEY_HEADER = "X-API-Key"
JWT_ALGORITHM = "HS256"
JWT_EXPIRY_HOURS = 24


# Security schemes
bearer_scheme = HTTPBearer(auto_error=False)
api_key_header = APIKeyHeader(name=API_KEY_HEADER, auto_error=False)


class TokenPayload(BaseModel):
    """JWT 페이로드"""
    sub: str  # subject (user_id)
    exp: int  # expiry timestamp
    iat: int  # issued at
    scopes: list[str] = []


class APIKeyInfo(BaseModel):
    """API Key 정보"""
    key_id: str
    client_id: str
    scopes: list[str]
    created_at: datetime
    expires_at: Optional[datetime] = None


# In-memory API keys (프로덕션에서는 DB 사용)
API_KEYS = {
    "autus_dev_key_123": APIKeyInfo(
        key_id="dev_001",
        client_id="development",
        scopes=["read", "write", "admin"],
        created_at=datetime.now()
    ),
    "autus_test_key_456": APIKeyInfo(
        key_id="test_001",
        client_id="testing",
        scopes=["read", "write"],
        created_at=datetime.now()
    )
}


def create_jwt_token(user_id: str, scopes: list[str] = None) -> str:
    """JWT 토큰 생성"""
    now = datetime.utcnow()
    payload = {
        "sub": user_id,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(hours=JWT_EXPIRY_HOURS)).timestamp()),
        "scopes": scopes or []
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=JWT_ALGORITHM)


def decode_jwt_token(token: str) -> Optional[TokenPayload]:
    """JWT 토큰 디코드"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[JWT_ALGORITHM])
        return TokenPayload(**payload)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        return None


def validate_api_key(api_key: str) -> Optional[APIKeyInfo]:
    """API Key 검증"""
    return API_KEYS.get(api_key)


def generate_api_key(client_id: str, scopes: list[str] = None) -> str:
    """새 API Key 생성"""
    timestamp = str(time.time())
    raw = f"{client_id}:{timestamp}:{SECRET_KEY}"
    key = f"autus_{hashlib.sha256(raw.encode()).hexdigest()[:32]}"
    
    API_KEYS[key] = APIKeyInfo(
        key_id=f"key_{len(API_KEYS) + 1}",
        client_id=client_id,
        scopes=scopes or ["read"],
        created_at=datetime.now()
    )
    
    return key


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    api_key: str = Depends(api_key_header)
) -> Optional[dict]:
    """
    현재 사용자 가져오기
    
    인증 우선순위:
    1. Bearer Token (JWT)
    2. API Key (X-API-Key header)
    """
    # 1. JWT 토큰 확인
    if credentials:
        token_data = decode_jwt_token(credentials.credentials)
        if token_data:
            return {
                "type": "jwt",
                "user_id": token_data.sub,
                "scopes": token_data.scopes
            }
    
    # 2. API Key 확인
    if api_key:
        key_info = validate_api_key(api_key)
        if key_info:
            return {
                "type": "api_key",
                "client_id": key_info.client_id,
                "scopes": key_info.scopes
            }
    
    return None


async def require_auth(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    api_key: str = Depends(api_key_header)
) -> dict:
    """인증 필수"""
    user = await get_current_user(credentials, api_key)
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"}
        )
    return user


def require_scope(required_scope: str):
    """특정 스코프 필수"""
    async def scope_checker(user: dict = Depends(require_auth)) -> dict:
        if required_scope not in user.get("scopes", []):
            raise HTTPException(
                status_code=403,
                detail=f"Scope '{required_scope}' required"
            )
        return user
    return scope_checker


async def optional_auth(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    api_key: str = Depends(api_key_header)
) -> Optional[dict]:
    """인증 선택적"""
    return await get_current_user(credentials, api_key)


# Rate Limiting
class RateLimiter:
    """요청 제한"""
    
    def __init__(self, max_requests: int = 100, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests = {}  # {client_id: [(timestamp, count)]}
    
    def _clean_old_requests(self, client_id: str):
        """오래된 요청 정리"""
        cutoff = time.time() - self.window_seconds
        if client_id in self.requests:
            self.requests[client_id] = [
                (ts, count) for ts, count in self.requests[client_id]
                if ts > cutoff
            ]
    
    def is_allowed(self, client_id: str) -> bool:
        """요청 허용 여부"""
        self._clean_old_requests(client_id)
        
        if client_id not in self.requests:
            self.requests[client_id] = []
        
        total = sum(count for _, count in self.requests[client_id])
        
        if total >= self.max_requests:
            return False
        
        self.requests[client_id].append((time.time(), 1))
        return True
    
    def get_remaining(self, client_id: str) -> int:
        """남은 요청 수"""
        self._clean_old_requests(client_id)
        total = sum(count for _, count in self.requests.get(client_id, []))
        return max(0, self.max_requests - total)


# 글로벌 Rate Limiter
rate_limiter = RateLimiter(max_requests=100, window_seconds=60)


def check_rate_limit(client_id: str = "anonymous"):
    """Rate Limit 체크 의존성"""
    async def checker(user: dict = Depends(optional_auth)) -> None:
        cid = user.get("client_id") or user.get("user_id") if user else client_id
        
        if not rate_limiter.is_allowed(cid):
            remaining = rate_limiter.get_remaining(cid)
            raise HTTPException(
                status_code=429,
                detail="Too many requests",
                headers={
                    "X-RateLimit-Remaining": str(remaining),
                    "X-RateLimit-Reset": str(rate_limiter.window_seconds)
                }
            )
    return checker


