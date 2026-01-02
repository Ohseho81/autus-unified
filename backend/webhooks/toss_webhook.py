# backend/webhooks/toss_webhook.py
# 토스페이먼츠 결제 웹훅 처리

from fastapi import APIRouter, Request, HTTPException, Header
import os
from typing import Optional
from integrations.zero_meaning import ZeroMeaningCleaner
from integrations.neo4j_client import Neo4jClient

router = APIRouter()
cleaner = ZeroMeaningCleaner()
neo4j = Neo4jClient()

TOSS_SECRET_KEY = os.getenv("TOSS_SECRET_KEY", "test_sk_xxx")

@router.post("")
async def toss_webhook(request: Request):
    """
    토스페이먼츠 웹훅 엔드포인트
    
    지원 이벤트:
    - DONE (결제 완료) → inflow
    - CANCELED (결제 취소) → outflow
    - PARTIAL_CANCELED (부분 취소) → outflow
    """
    import json
    data = await request.json()
    
    event_type = data.get("status", "")
    
    # Zero Meaning 정제
    cleaned = {
        "node_id": data.get("orderId", "").split("_")[0] if "_" in data.get("orderId", "") else data.get("orderId"),
        "value": float(data.get("totalAmount", 0)),
        "timestamp": data.get("approvedAt") or data.get("requestedAt")
    }
    
    result = {"status": event_type, "processed": False}
    
    if event_type == "DONE":
        # 결제 완료 → inflow
        node = await neo4j.upsert_node(
            external_id=cleaned["node_id"],
            source="toss"
        )
        
        motion = await neo4j.create_motion(
            source_id=cleaned["node_id"],
            target_id="owner",
            amount=cleaned["value"],
            direction="inflow"
        )
        
        result = {
            "status": event_type,
            "node": node,
            "motion": motion,
            "amount": cleaned["value"],
            "processed": True
        }
    
    elif event_type in ["CANCELED", "PARTIAL_CANCELED"]:
        # 취소 → outflow
        cancel_amount = float(data.get("cancels", [{}])[0].get("cancelAmount", 0)) if data.get("cancels") else cleaned["value"]
        
        motion = await neo4j.create_motion(
            source_id="owner",
            target_id=cleaned["node_id"],
            amount=cancel_amount,
            direction="outflow"
        )
        
        result = {
            "status": event_type,
            "motion": motion,
            "amount": cancel_amount,
            "processed": True
        }
    
    return result


@router.post("/virtual-account")
async def toss_virtual_account_webhook(request: Request):
    """
    가상계좌 입금 확인 웹훅 (수수료 0%)
    
    입금 완료 시 자동 처리
    """
    data = await request.json()
    
    # 입금 완료 확인
    if data.get("status") != "DONE":
        return {"processed": False, "reason": "Not completed"}
    
    # Zero Meaning 정제
    cleaned = {
        "node_id": data.get("orderId", "").split("_")[0],
        "value": float(data.get("totalAmount", 0)),
        "method": "virtual_account",
        "fee": 0  # 수수료 0%
    }
    
    # 노드 생성/업데이트
    node = await neo4j.upsert_node(
        external_id=cleaned["node_id"],
        source="toss_va"
    )
    
    # inflow 모션 생성
    motion = await neo4j.create_motion(
        source_id=cleaned["node_id"],
        target_id="owner",
        amount=cleaned["value"],
        direction="inflow"
    )
    
    return {
        "status": "DONE",
        "method": "virtual_account",
        "fee": 0,
        "node": node,
        "motion": motion,
        "processed": True
    }
