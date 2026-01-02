# backend/main.py
# AUTUS 통합 API - 모든 기능 포함

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

# 라우터 임포트
from webhooks.stripe_webhook import router as stripe_router
from webhooks.shopify_webhook import router as shopify_router
from webhooks.toss_webhook import router as toss_router
from webhooks.universal_webhook import router as universal_router
from crewai.api import router as crewai_router
from parasitic.api import router as parasitic_router
from autosync.api import router as autosync_router
from auth.api import router as auth_router
from websocket.api import router as ws_router, http_router as ws_http_router
from physics.router import router as physics_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    """앱 라이프사이클"""
    print("🚀 AUTUS Integration Hub 시작")
    print("   - Auth: JWT + API Key 인증")
    print("   - WebSocket: 실시간 Physics Map")
    print("   - Physics: 물리 엔진 API")
    yield
    print("👋 AUTUS Integration Hub 종료")

app = FastAPI(
    title="AUTUS Integration Hub",
    description="""
## AUTUS 통합 API

### 기능
- **Auth**: JWT 토큰 + API Key 인증
- **Webhooks**: Stripe, Shopify, 토스, 범용
- **CrewAI**: 삭제/자동화/외부용역 분석
- **Parasitic**: 기존 SaaS 흡수/대체
- **AutoSync**: 30+ SaaS 자동 감지/연동
- **Physics**: Money Physics 엔진 + 시뮬레이션
- **WebSocket**: 실시간 업데이트

### 인증
- Bearer Token (JWT): `Authorization: Bearer <token>`
- API Key: `X-API-Key: <api_key>`

### 테스트 계정
- admin / admin123 (모든 권한)
- user / user123 (read, write)

### 철학
- Zero Meaning: 의미 제거, 숫자만
- Money Physics: 사람 = 노드, 돈 = 에너지
- Flywheel: 삭제 → 자동화 → 시너지 → 가속
    """,
    version="2.1.0",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 등록
app.include_router(auth_router, tags=["Authentication"])
app.include_router(stripe_router, prefix="/webhook/stripe", tags=["Webhook - Stripe"])
app.include_router(shopify_router, prefix="/webhook/shopify", tags=["Webhook - Shopify"])
app.include_router(toss_router, prefix="/webhook/toss", tags=["Webhook - Toss"])
app.include_router(universal_router, prefix="/webhook/universal", tags=["Webhook - Universal"])
app.include_router(crewai_router, tags=["CrewAI Analysis"])
app.include_router(parasitic_router, tags=["Parasitic Absorption"])
app.include_router(autosync_router, tags=["AutoSync"])
app.include_router(physics_router, tags=["Physics Engine"])
app.include_router(ws_router, tags=["WebSocket"])
app.include_router(ws_http_router, tags=["WebSocket API"])


@app.get("/")
async def root():
    """API 정보"""
    return {
        "name": "AUTUS Integration Hub",
        "service": "AUTUS Integration Hub",
        "version": "2.1.0",
        "philosophy": "Zero Meaning + Money Physics + Flywheel",
        "endpoints": {
            "auth": [
                "/auth/login",
                "/auth/api-key",
                "/auth/me",
                "/auth/rate-limit"
            ],
            "physics": [
                "/physics/state",
                "/physics/kpi",
                "/physics/predict",
                "/physics/event",
                "/physics/drag"
            ],
            "websocket": [
                "ws://localhost:8000/ws/physics-map",
                "ws://localhost:8000/ws/dashboard",
                "ws://localhost:8000/ws/flywheel",
                "/websocket/stats",
                "/websocket/broadcast/test"
            ],
            "webhooks": [
                "/webhook/stripe",
                "/webhook/shopify",
                "/webhook/toss",
                "/webhook/universal"
            ],
            "crewai": [
                "/crewai/analyze",
                "/crewai/quick-delete",
                "/crewai/quick-automate"
            ],
            "parasitic": [
                "/parasitic/connect",
                "/parasitic/absorb/{id}",
                "/parasitic/replace/{id}",
                "/parasitic/status"
            ],
            "autosync": [
                "/autosync/systems",
                "/autosync/detect",
                "/autosync/transform",
                "/autosync/connect"
            ]
        }
    }


@app.get("/health")
async def health():
    """헬스체크"""
    return {
        "status": "healthy",
        "services": {
            "auth": "ok",
            "webhooks": "ok",
            "crewai": "ok",
            "parasitic": "ok",
            "autosync": "ok",
            "physics": "ok",
            "websocket": "ok"
        }
    }


@app.get("/strategy")
async def strategy():
    """AUTUS 핵심 전략"""
    return {
        "core_strategies": [
            {
                "name": "결제 수수료 0%",
                "description": "가상계좌 QR로 카드 수수료 3% 제거",
                "trigger": True,
                "monthly_savings": "매출의 3%"
            },
            {
                "name": "Parasitic Absorption",
                "description": "기존 SaaS 연동 → 데이터 흡수 → 완전 대체",
                "stages": ["PARASITIC", "ABSORBING", "REPLACING", "REPLACED"]
            },
            {
                "name": "Money Flywheel",
                "description": "삭제 70% + 자동화 20% + 시너지 10%",
                "formula": "V = (M - T) × (1 + s)^t"
            }
        ],
        "projected_roi": {
            "3_months": "3x",
            "6_months": "6.7x",
            "12_months": "21.7x"
        }
    }


# 직접 실행 시
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

