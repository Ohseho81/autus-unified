# backend/webhooks/universal_webhook.py
# 범용 웹훅 - 자동 소스 감지 + WebSocket 실시간 전송

from fastapi import APIRouter, Request, Header
from typing import Optional
from integrations.zero_meaning import ZeroMeaningCleaner
from integrations.neo4j_client import Neo4jClient
from websocket import (
    broadcast_node_update,
    broadcast_motion_update,
    broadcast_webhook_received
)

router = APIRouter()
cleaner = ZeroMeaningCleaner()
neo4j = Neo4jClient()

def detect_source(headers: dict, data: dict) -> str:
    """웹훅 소스 자동 감지"""
    # Header 기반 감지
    if "stripe-signature" in headers:
        return "stripe"
    if "x-shopify-hmac-sha256" in headers:
        return "shopify"
    if "x-quickbooks-signature" in headers:
        return "quickbooks"
    if "x-paddle-signature" in headers:
        return "paddle"
    
    # Data 기반 감지
    if "livemode" in data and "api_version" in data:
        return "stripe"
    if "admin_graphql_api_id" in data:
        return "shopify"
    if "realmId" in data:
        return "quickbooks"
    if "event_type" in data and "passthrough" in data:
        return "paddle"
    
    return "unknown"

def detect_flow_type(data: dict, source: str) -> str:
    """이벤트 타입으로 flow 방향 감지"""
    event = data.get("type", "") or data.get("topic", "") or data.get("event_type", "")
    
    inflow_keywords = ["succeeded", "paid", "completed", "create", "payment"]
    outflow_keywords = ["refund", "cancel", "void", "chargeback"]
    
    event_lower = event.lower()
    
    for keyword in outflow_keywords:
        if keyword in event_lower:
            return "outflow"
    
    for keyword in inflow_keywords:
        if keyword in event_lower:
            return "inflow"
    
    # 금액 기반 추론
    amount = data.get("amount") or data.get("total") or data.get("total_price", 0)
    if float(amount) > 0:
        return "inflow"
    
    return "unknown"

@router.post("")
async def universal_webhook(
    request: Request,
    stripe_signature: Optional[str] = Header(None, alias="stripe-signature"),
    x_shopify_hmac: Optional[str] = Header(None, alias="x-shopify-hmac-sha256"),
    x_shopify_topic: Optional[str] = Header(None, alias="x-shopify-topic")
):
    """
    범용 웹훅 엔드포인트
    
    자동 처리:
    1. 소스 자동 감지 (Stripe, Shopify, QuickBooks 등)
    2. Zero Meaning 정제
    3. Flow 타입 감지 (inflow/outflow)
    4. 노드/모션 자동 생성
    """
    import json
    
    payload = await request.body()
    data = json.loads(payload)
    
    # 헤더 수집
    headers = {
        "stripe-signature": stripe_signature,
        "x-shopify-hmac-sha256": x_shopify_hmac,
        "x-shopify-topic": x_shopify_topic
    }
    
    # 1. 소스 감지
    source = detect_source(headers, data)
    
    # 2. Zero Meaning 정제
    cleaned = cleaner.cleanse(data, source=source)
    
    # 3. Flow 타입 감지
    flow_type = detect_flow_type(data, source)
    
    # 4. 처리
    result = {
        "source": source,
        "flow_type": flow_type,
        "cleaned": cleaned,
        "processed": False
    }
    
    if flow_type == "inflow":
        # 노드 생성/업데이트
        node = await neo4j.upsert_node(
            external_id=cleaned["node_id"],
            source=source
        )
        
        # inflow 모션
        motion = await neo4j.create_motion(
            source_id=cleaned["node_id"],
            target_id="owner",
            amount=cleaned["value"],
            direction="inflow"
        )
        
        result["node"] = node
        result["motion"] = motion
        result["processed"] = True
        
        # 🔴 WebSocket 실시간 전송
        await broadcast_node_update(cleaned["node_id"], cleaned["value"], source)
        await broadcast_motion_update(cleaned["node_id"], "owner", cleaned["value"])
        await broadcast_webhook_received(source, "inflow", cleaned["value"])
    
    elif flow_type == "outflow":
        # outflow 모션
        motion = await neo4j.create_motion(
            source_id="owner",
            target_id=cleaned["node_id"],
            amount=cleaned["value"],
            direction="outflow"
        )
        
        result["motion"] = motion
        result["processed"] = True
        
        # 🔴 WebSocket 실시간 전송
        await broadcast_motion_update("owner", cleaned["node_id"], cleaned["value"])
        await broadcast_webhook_received(source, "outflow", cleaned["value"])
    
    return result
