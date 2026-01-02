# backend/webhooks/main.py
# 모든 SaaS 웹훅 통합 라우터

from fastapi import FastAPI, Request, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
import hmac
import hashlib
from typing import Optional

from .stripe_webhook import router as stripe_router
from .shopify_webhook import router as shopify_router
from .toss_webhook import router as toss_router
from .universal_webhook import router as universal_router

app = FastAPI(title="AUTUS Integration Hub", version="1.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 등록
app.include_router(stripe_router, prefix="/webhook/stripe", tags=["Stripe"])
app.include_router(shopify_router, prefix="/webhook/shopify", tags=["Shopify"])
app.include_router(toss_router, prefix="/webhook/toss", tags=["Toss"])
app.include_router(universal_router, prefix="/webhook/universal", tags=["Universal"])

@app.get("/health")
async def health():
    return {"status": "ok", "service": "AUTUS Integration Hub"}

@app.get("/")
async def root():
    return {
        "service": "AUTUS Integration Hub",
        "endpoints": [
            "/webhook/stripe",
            "/webhook/shopify", 
            "/webhook/toss",
            "/webhook/universal"
        ]
    }
