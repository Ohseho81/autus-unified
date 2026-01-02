# backend/auth/api.py
# 인증 API 라우터

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

from .middleware import (
    create_jwt_token,
    generate_api_key,
    require_auth,
    require_scope,
    rate_limiter
)

router = APIRouter(prefix="/auth", tags=["Authentication"])


class LoginRequest(BaseModel):
    """로그인 요청"""
    username: str
    password: str


class TokenResponse(BaseModel):
    """토큰 응답"""
    access_token: str
    token_type: str = "bearer"
    expires_in: int = 86400  # 24시간


class APIKeyRequest(BaseModel):
    """API Key 생성 요청"""
    client_name: str
    scopes: Optional[list[str]] = None


class APIKeyResponse(BaseModel):
    """API Key 응답"""
    api_key: str
    client_name: str
    scopes: list[str]
    created_at: datetime


# 임시 사용자 DB (프로덕션에서는 실제 DB 사용)
USERS = {
    "admin": {"password": "admin123", "scopes": ["read", "write", "admin"]},
    "user": {"password": "user123", "scopes": ["read", "write"]},
    "readonly": {"password": "readonly123", "scopes": ["read"]}
}


@router.post("/login", response_model=TokenResponse)
async def login(req: LoginRequest):
    """
    로그인 및 JWT 토큰 발급
    
    테스트 계정:
    - admin / admin123 (모든 권한)
    - user / user123 (read, write)
    - readonly / readonly123 (read만)
    """
    user = USERS.get(req.username)
    
    if not user or user["password"] != req.password:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    token = create_jwt_token(req.username, user["scopes"])
    
    return TokenResponse(access_token=token)


@router.post("/api-key", response_model=APIKeyResponse)
async def create_api_key(
    req: APIKeyRequest,
    user: dict = Depends(require_scope("admin"))
):
    """
    API Key 생성 (admin 권한 필요)
    """
    scopes = req.scopes or ["read"]
    api_key = generate_api_key(req.client_name, scopes)
    
    return APIKeyResponse(
        api_key=api_key,
        client_name=req.client_name,
        scopes=scopes,
        created_at=datetime.now()
    )


@router.get("/me")
async def get_me(user: dict = Depends(require_auth)):
    """현재 인증 정보"""
    return {
        "authenticated": True,
        "auth_type": user.get("type"),
        "user_id": user.get("user_id"),
        "client_id": user.get("client_id"),
        "scopes": user.get("scopes", [])
    }


@router.get("/rate-limit")
async def get_rate_limit(user: dict = Depends(require_auth)):
    """Rate Limit 상태"""
    client_id = user.get("client_id") or user.get("user_id")
    remaining = rate_limiter.get_remaining(client_id)
    
    return {
        "client_id": client_id,
        "limit": rate_limiter.max_requests,
        "remaining": remaining,
        "window_seconds": rate_limiter.window_seconds
    }


@router.post("/refresh")
async def refresh_token(user: dict = Depends(require_auth)):
    """토큰 갱신"""
    if user.get("type") != "jwt":
        raise HTTPException(status_code=400, detail="Only JWT tokens can be refreshed")
    
    new_token = create_jwt_token(user["user_id"], user["scopes"])
    
    return TokenResponse(access_token=new_token)
