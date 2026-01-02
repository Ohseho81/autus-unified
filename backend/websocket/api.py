# backend/websocket/api.py
# WebSocket API 엔드포인트

import uuid
import json
from typing import Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from .manager import (
    manager, 
    Message,
    broadcast_node_update,
    broadcast_motion_update,
    broadcast_synergy_update
)

router = APIRouter(prefix="/ws", tags=["WebSocket"])


@router.websocket("/physics-map")
async def websocket_physics_map(
    websocket: WebSocket,
    client_id: Optional[str] = Query(None)
):
    """
    Physics Map 실시간 WebSocket
    
    연결: ws://localhost:8000/ws/physics-map?client_id=xxx
    
    수신 메시지 타입:
    - node_update: 노드 값 변경 (펄스 애니메이션)
    - motion_update: 모션 발생 (흐름 애니메이션)
    - synergy_update: 시너지 변경
    - flywheel_pulse: 플라이휠 단계 진행
    
    송신 메시지:
    - subscribe: 특정 노드 구독
    - unsubscribe: 구독 해제
    - ping: 연결 확인
    """
    cid = client_id or f"client_{uuid.uuid4().hex[:8]}"
    
    await manager.connect(websocket, cid, channels=["physics-map", "all"])
    
    try:
        while True:
            # 클라이언트 메시지 수신
            data = await websocket.receive_json()
            
            msg_type = data.get("type")
            
            if msg_type == "ping":
                # 핑-퐁
                await manager.send_personal(cid, Message(
                    type="pong",
                    data={"client_id": cid}
                ))
            
            elif msg_type == "subscribe":
                # 특정 노드 구독 (향후 구현)
                node_ids = data.get("node_ids", [])
                await manager.send_personal(cid, Message(
                    type="subscribed",
                    data={"node_ids": node_ids}
                ))
            
            elif msg_type == "request_state":
                # 현재 상태 요청
                await manager.send_personal(cid, Message(
                    type="state",
                    data={
                        "nodes": [],  # TODO: 실제 노드 데이터
                        "motions": [],
                        "synergy": 1.0
                    }
                ))
            
            else:
                # 알 수 없는 메시지
                await manager.send_personal(cid, Message(
                    type="error",
                    data={"message": f"Unknown message type: {msg_type}"}
                ))
    
    except WebSocketDisconnect:
        manager.disconnect(cid)
    except Exception as e:
        print(f"WebSocket 에러 ({cid}): {e}")
        manager.disconnect(cid)


@router.websocket("/dashboard")
async def websocket_dashboard(
    websocket: WebSocket,
    client_id: Optional[str] = Query(None)
):
    """
    대시보드 실시간 WebSocket
    
    수신 메시지 타입:
    - webhook_received: Webhook 수신 알림
    - parasitic_progress: Parasitic 진행 상황
    - crewai_result: CrewAI 분석 결과
    """
    cid = client_id or f"dash_{uuid.uuid4().hex[:8]}"
    
    await manager.connect(websocket, cid, channels=["dashboard", "all"])
    
    try:
        while True:
            data = await websocket.receive_json()
            
            if data.get("type") == "ping":
                await manager.send_personal(cid, Message(
                    type="pong",
                    data={"client_id": cid}
                ))
    
    except WebSocketDisconnect:
        manager.disconnect(cid)


@router.websocket("/flywheel")
async def websocket_flywheel(
    websocket: WebSocket,
    client_id: Optional[str] = Query(None)
):
    """
    Flywheel 실시간 WebSocket
    
    수신 메시지 타입:
    - flywheel_pulse: 플라이휠 단계 진행
    - momentum_update: 모멘텀 변화
    """
    cid = client_id or f"fly_{uuid.uuid4().hex[:8]}"
    
    await manager.connect(websocket, cid, channels=["flywheel", "all"])
    
    try:
        while True:
            data = await websocket.receive_json()
            
            if data.get("type") == "ping":
                await manager.send_personal(cid, Message(
                    type="pong",
                    data={"client_id": cid}
                ))
    
    except WebSocketDisconnect:
        manager.disconnect(cid)


# ═══════════════════════════════════════════════════════════════
# HTTP API (WebSocket 상태 확인 및 테스트용)
# ═══════════════════════════════════════════════════════════════

from fastapi import APIRouter as HTTPRouter

http_router = HTTPRouter(prefix="/websocket", tags=["WebSocket API"])


@http_router.get("/stats")
async def get_stats():
    """WebSocket 통계"""
    return manager.get_stats()


@http_router.get("/clients")
async def get_clients():
    """연결된 클라이언트 목록"""
    return {
        "clients": manager.get_clients(),
        "count": len(manager.active_connections)
    }


@http_router.post("/broadcast/test")
async def broadcast_test(node_id: str = "test_node", value: float = 100000):
    """
    테스트 브로드캐스트
    
    Physics Map에 테스트 노드 업데이트 전송
    """
    await broadcast_node_update(node_id, value, source="test")
    return {
        "success": True,
        "message": f"Broadcasted node_update: {node_id} = {value}",
        "active_clients": len(manager.active_connections)
    }


@http_router.post("/broadcast/motion")
async def broadcast_motion_test(
    source: str = "node_001",
    target: str = "node_002",
    amount: float = 50000
):
    """테스트 모션 브로드캐스트"""
    await broadcast_motion_update(source, target, amount)
    return {
        "success": True,
        "message": f"Broadcasted motion: {source} → {target} = {amount}"
    }


@http_router.post("/broadcast/synergy")
async def broadcast_synergy_test(synergy: float = 1.5, total_value: float = 1000000):
    """테스트 시너지 브로드캐스트"""
    await broadcast_synergy_update(synergy, total_value)
    return {
        "success": True,
        "message": f"Broadcasted synergy: {synergy}x, total: {total_value}"
    }
