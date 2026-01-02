# backend/webhooks/shopify_webhook.py
# Shopify 주문/고객 웹훅 처리

from fastapi import APIRouter, Request, HTTPException, Header
import hmac
import hashlib
import base64
import os
from typing import Optional
from integrations.zero_meaning import ZeroMeaningCleaner
from integrations.neo4j_client import Neo4jClient

router = APIRouter()
cleaner = ZeroMeaningCleaner()
neo4j = Neo4jClient()

SHOPIFY_API_SECRET = os.getenv("SHOPIFY_API_SECRET", "shpss_xxx")

def verify_shopify_hmac(payload: bytes, hmac_header: str, secret: str) -> bool:
    """Shopify HMAC 검증"""
    try:
        computed = base64.b64encode(
            hmac.new(secret.encode(), payload, hashlib.sha256).digest()
        ).decode()
        return hmac.compare_digest(computed, hmac_header)
    except:
        return False

@router.post("")
async def shopify_webhook(
    request: Request,
    x_shopify_hmac_sha256: Optional[str] = Header(None),
    x_shopify_topic: Optional[str] = Header(None),
    x_shopify_shop_domain: Optional[str] = Header(None)
):
    """
    Shopify 웹훅 엔드포인트
    
    지원 이벤트:
    - orders/create → inflow
    - orders/paid → inflow
    - orders/cancelled → outflow
    - refunds/create → outflow
    - customers/create → node_create
    """
    payload = await request.body()
    
    # HMAC 검증
    if x_shopify_hmac_sha256 and SHOPIFY_API_SECRET != "shpss_xxx":
        if not verify_shopify_hmac(payload, x_shopify_hmac_sha256, SHOPIFY_API_SECRET):
            raise HTTPException(status_code=401, detail="Invalid HMAC")
    
    import json
    data = json.loads(payload)
    
    topic = x_shopify_topic or ""
    
    # Zero Meaning 정제
    cleaned = cleaner.cleanse(data, source="shopify")
    
    result = {"topic": topic, "processed": False}
    
    if topic in ["orders/create", "orders/paid"]:
        # 주문 생성/결제 → inflow
        # 고객 노드 (없으면 게스트)
        customer_id = cleaned.get("node_id") or f"guest_{data.get('id', 'unknown')}"
        
        node = await neo4j.upsert_node(
            external_id=customer_id,
            source="shopify"
        )
        
        motion = await neo4j.create_motion(
            source_id=customer_id,
            target_id="owner",
            amount=cleaned["value"],
            direction="inflow"
        )
        
        result = {"topic": topic, "node": node, "motion": motion, "processed": True}
    
    elif topic == "orders/cancelled":
        # 주문 취소 → outflow (환불)
        customer_id = cleaned.get("node_id") or f"guest_{data.get('id', 'unknown')}"
        
        motion = await neo4j.create_motion(
            source_id="owner",
            target_id=customer_id,
            amount=cleaned["value"],
            direction="outflow"
        )
        
        result = {"topic": topic, "motion": motion, "processed": True}
    
    elif topic == "refunds/create":
        # 환불 → outflow
        customer_id = cleaned.get("node_id") or "unknown"
        refund_amount = sum(
            float(item.get("subtotal", 0)) 
            for item in data.get("refund_line_items", [])
        )
        
        motion = await neo4j.create_motion(
            source_id="owner",
            target_id=customer_id,
            amount=refund_amount,
            direction="outflow"
        )
        
        result = {"topic": topic, "motion": motion, "processed": True}
    
    elif topic == "customers/create":
        # 고객 생성 → 노드 생성
        node = await neo4j.upsert_node(
            external_id=cleaned["node_id"],
            source="shopify"
        )
        
        result = {"topic": topic, "node": node, "processed": True}
    
    return result
