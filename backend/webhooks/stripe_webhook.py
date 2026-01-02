# backend/webhooks/stripe_webhook.py
# Stripe 결제 웹훅 처리

from fastapi import APIRouter, Request, HTTPException, Header
import hmac
import hashlib
import os
from typing import Optional
from integrations.zero_meaning import ZeroMeaningCleaner
from integrations.neo4j_client import Neo4jClient

router = APIRouter()
cleaner = ZeroMeaningCleaner()
neo4j = Neo4jClient()

STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "whsec_xxx")

def verify_stripe_signature(payload: bytes, sig_header: str, secret: str) -> bool:
    """Stripe 서명 검증"""
    try:
        timestamp, signature = None, None
        for item in sig_header.split(","):
            key, value = item.split("=")
            if key == "t":
                timestamp = value
            elif key == "v1":
                signature = value
        
        signed_payload = f"{timestamp}.{payload.decode()}"
        expected = hmac.new(
            secret.encode(),
            signed_payload.encode(),
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(expected, signature)
    except:
        return False

@router.post("")
async def stripe_webhook(
    request: Request,
    stripe_signature: Optional[str] = Header(None, alias="stripe-signature")
):
    """
    Stripe 웹훅 엔드포인트
    
    지원 이벤트:
    - payment_intent.succeeded → inflow
    - charge.refunded → outflow
    - customer.created → node_create
    - invoice.paid → inflow
    """
    payload = await request.body()
    
    # 서명 검증
    if stripe_signature and STRIPE_WEBHOOK_SECRET != "whsec_xxx":
        if not verify_stripe_signature(payload, stripe_signature, STRIPE_WEBHOOK_SECRET):
            raise HTTPException(status_code=400, detail="Invalid signature")
    
    import json
    data = json.loads(payload)
    
    event_type = data.get("type", "")
    event_data = data.get("data", {}).get("object", {})
    
    # Zero Meaning 정제
    cleaned = cleaner.cleanse(event_data, source="stripe")
    
    # 이벤트별 처리
    result = {"event": event_type, "processed": False}
    
    if event_type == "payment_intent.succeeded":
        # 결제 성공 → inflow 모션 생성
        node = await neo4j.upsert_node(
            external_id=cleaned["node_id"],
            source="stripe"
        )
        motion = await neo4j.create_motion(
            source_id=cleaned["node_id"],
            target_id="owner",
            amount=cleaned["value"],
            direction="inflow"
        )
        result = {"event": event_type, "node": node, "motion": motion, "processed": True}
    
    elif event_type == "charge.refunded":
        # 환불 → outflow 모션 생성
        motion = await neo4j.create_motion(
            source_id="owner",
            target_id=cleaned["node_id"],
            amount=cleaned["value"],
            direction="outflow"
        )
        result = {"event": event_type, "motion": motion, "processed": True}
    
    elif event_type == "customer.created":
        # 고객 생성 → 노드 생성
        node = await neo4j.upsert_node(
            external_id=cleaned["node_id"],
            source="stripe"
        )
        result = {"event": event_type, "node": node, "processed": True}
    
    elif event_type == "invoice.paid":
        # 인보이스 결제 → inflow
        motion = await neo4j.create_motion(
            source_id=cleaned["node_id"],
            target_id="owner",
            amount=cleaned["value"],
            direction="inflow"
        )
        result = {"event": event_type, "motion": motion, "processed": True}
    
    return result
