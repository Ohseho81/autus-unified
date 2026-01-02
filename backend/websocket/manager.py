# backend/websocket/manager.py
# WebSocket 연결 관리자

import json
import asyncio
from typing import Dict, List, Set, Optional, Any
from datetime import datetime
from fastapi import WebSocket, WebSocketDisconnect
from pydantic import BaseModel


class Message(BaseModel):
    """WebSocket 메시지"""
    type: str  # node_update, motion_update, synergy_update, flywheel_pulse
    data: Dict[str, Any]
    timestamp: str = None
    
    def __init__(self, **data):
        if not data.get('timestamp'):
            data['timestamp'] = datetime.now().isoformat()
        super().__init__(**data)


class ConnectionManager:
    """
    WebSocket 연결 관리자
    
    기능:
    - 다중 클라이언트 연결 관리
    - 채널별 구독 (physics-map, dashboard, etc.)
    - 브로드캐스트 / 특정 클라이언트 전송
    - 자동 재연결 지원
    """
    
    def __init__(self):
        # 활성 연결: {client_id: WebSocket}
        self.active_connections: Dict[str, WebSocket] = {}
        
        # 채널별 구독자: {channel: Set[client_id]}
        self.channels: Dict[str, Set[str]] = {
            "physics-map": set(),
            "dashboard": set(),
            "flywheel": set(),
            "all": set()
        }
        
        # 연결 메타데이터: {client_id: {connected_at, channels, ...}}
        self.metadata: Dict[str, Dict] = {}
        
        # 메시지 큐 (재연결 시 전송용)
        self.message_queue: Dict[str, List[Message]] = {}
        
        # 통계
        self.stats = {
            "total_connections": 0,
            "total_messages": 0,
            "messages_per_channel": {}
        }
    
    async def connect(
        self, 
        websocket: WebSocket, 
        client_id: str,
        channels: List[str] = None
    ):
        """클라이언트 연결"""
        await websocket.accept()
        
        self.active_connections[client_id] = websocket
        self.metadata[client_id] = {
            "connected_at": datetime.now().isoformat(),
            "channels": channels or ["all"],
            "message_count": 0
        }
        
        # 채널 구독
        subscribe_channels = channels or ["all"]
        for channel in subscribe_channels:
            if channel not in self.channels:
                self.channels[channel] = set()
            self.channels[channel].add(client_id)
        
        self.stats["total_connections"] += 1
        
        # 연결 성공 메시지
        await self.send_personal(client_id, Message(
            type="connected",
            data={
                "client_id": client_id,
                "channels": subscribe_channels,
                "server_time": datetime.now().isoformat()
            }
        ))
        
        # 큐에 있는 메시지 전송
        if client_id in self.message_queue:
            for msg in self.message_queue[client_id]:
                await self.send_personal(client_id, msg)
            del self.message_queue[client_id]
        
        print(f"✅ WebSocket 연결: {client_id} → {subscribe_channels}")
    
    def disconnect(self, client_id: str):
        """클라이언트 연결 해제"""
        if client_id in self.active_connections:
            del self.active_connections[client_id]
        
        # 모든 채널에서 제거
        for channel in self.channels.values():
            channel.discard(client_id)
        
        if client_id in self.metadata:
            del self.metadata[client_id]
        
        print(f"❌ WebSocket 해제: {client_id}")
    
    async def send_personal(self, client_id: str, message: Message):
        """특정 클라이언트에 전송"""
        if client_id in self.active_connections:
            try:
                websocket = self.active_connections[client_id]
                await websocket.send_json(message.dict())
                
                if client_id in self.metadata:
                    self.metadata[client_id]["message_count"] += 1
                
                self.stats["total_messages"] += 1
            except Exception as e:
                print(f"전송 실패 ({client_id}): {e}")
                self.disconnect(client_id)
        else:
            # 연결 없으면 큐에 저장
            if client_id not in self.message_queue:
                self.message_queue[client_id] = []
            self.message_queue[client_id].append(message)
    
    async def broadcast(self, message: Message, channel: str = "all"):
        """채널에 브로드캐스트"""
        if channel not in self.channels:
            return
        
        # 통계
        if channel not in self.stats["messages_per_channel"]:
            self.stats["messages_per_channel"][channel] = 0
        self.stats["messages_per_channel"][channel] += 1
        
        # 채널 구독자들에게 전송
        disconnected = []
        for client_id in self.channels[channel]:
            if client_id in self.active_connections:
                try:
                    websocket = self.active_connections[client_id]
                    await websocket.send_json(message.dict())
                    self.stats["total_messages"] += 1
                except Exception as e:
                    print(f"브로드캐스트 실패 ({client_id}): {e}")
                    disconnected.append(client_id)
        
        # 실패한 연결 정리
        for client_id in disconnected:
            self.disconnect(client_id)
    
    async def broadcast_all(self, message: Message):
        """모든 연결에 브로드캐스트"""
        disconnected = []
        for client_id, websocket in self.active_connections.items():
            try:
                await websocket.send_json(message.dict())
                self.stats["total_messages"] += 1
            except Exception as e:
                print(f"브로드캐스트 실패 ({client_id}): {e}")
                disconnected.append(client_id)
        
        for client_id in disconnected:
            self.disconnect(client_id)
    
    def get_stats(self) -> Dict:
        """통계 반환"""
        return {
            **self.stats,
            "active_connections": len(self.active_connections),
            "channels": {k: len(v) for k, v in self.channels.items()}
        }
    
    def get_clients(self) -> List[Dict]:
        """연결된 클라이언트 목록"""
        return [
            {
                "client_id": cid,
                **self.metadata.get(cid, {})
            }
            for cid in self.active_connections.keys()
        ]


# 글로벌 매니저 인스턴스
manager = ConnectionManager()


# ═══════════════════════════════════════════════════════════════
# 편의 함수 (다른 모듈에서 import하여 사용)
# ═══════════════════════════════════════════════════════════════

async def broadcast_node_update(node_id: str, value: float, source: str = "webhook"):
    """노드 업데이트 브로드캐스트"""
    await manager.broadcast(
        Message(
            type="node_update",
            data={
                "node_id": node_id,
                "value": value,
                "source": source,
                "action": "pulse"  # 프론트엔드에서 펄스 애니메이션
            }
        ),
        channel="physics-map"
    )


async def broadcast_motion_update(source_id: str, target_id: str, amount: float):
    """모션(엣지) 업데이트 브로드캐스트"""
    await manager.broadcast(
        Message(
            type="motion_update",
            data={
                "source": source_id,
                "target": target_id,
                "amount": amount,
                "action": "flow"  # 프론트엔드에서 흐름 애니메이션
            }
        ),
        channel="physics-map"
    )


async def broadcast_synergy_update(synergy: float, total_value: float):
    """시너지 업데이트 브로드캐스트"""
    await manager.broadcast(
        Message(
            type="synergy_update",
            data={
                "synergy": synergy,
                "total_value": total_value
            }
        ),
        channel="physics-map"
    )


async def broadcast_flywheel_pulse(stage: str, momentum: float):
    """플라이휠 펄스 브로드캐스트"""
    await manager.broadcast(
        Message(
            type="flywheel_pulse",
            data={
                "stage": stage,  # delete, automate, synergy, accelerate
                "momentum": momentum
            }
        ),
        channel="flywheel"
    )


async def broadcast_webhook_received(source: str, event_type: str, amount: float):
    """Webhook 수신 브로드캐스트 (대시보드용)"""
    await manager.broadcast(
        Message(
            type="webhook_received",
            data={
                "source": source,
                "event_type": event_type,
                "amount": amount
            }
        ),
        channel="dashboard"
    )

# backend/websocket/manager.py
# WebSocket 연결 관리자

import json
import asyncio
from typing import Dict, List, Set, Optional, Any
from datetime import datetime
from fastapi import WebSocket, WebSocketDisconnect
from pydantic import BaseModel


class Message(BaseModel):
    """WebSocket 메시지"""
    type: str  # node_update, motion_update, synergy_update, flywheel_pulse
    data: Dict[str, Any]
    timestamp: str = None
    
    def __init__(self, **data):
        if not data.get('timestamp'):
            data['timestamp'] = datetime.now().isoformat()
        super().__init__(**data)


class ConnectionManager:
    """
    WebSocket 연결 관리자
    
    기능:
    - 다중 클라이언트 연결 관리
    - 채널별 구독 (physics-map, dashboard, etc.)
    - 브로드캐스트 / 특정 클라이언트 전송
    - 자동 재연결 지원
    """
    
    def __init__(self):
        # 활성 연결: {client_id: WebSocket}
        self.active_connections: Dict[str, WebSocket] = {}
        
        # 채널별 구독자: {channel: Set[client_id]}
        self.channels: Dict[str, Set[str]] = {
            "physics-map": set(),
            "dashboard": set(),
            "flywheel": set(),
            "all": set()
        }
        
        # 연결 메타데이터: {client_id: {connected_at, channels, ...}}
        self.metadata: Dict[str, Dict] = {}
        
        # 메시지 큐 (재연결 시 전송용)
        self.message_queue: Dict[str, List[Message]] = {}
        
        # 통계
        self.stats = {
            "total_connections": 0,
            "total_messages": 0,
            "messages_per_channel": {}
        }
    
    async def connect(
        self, 
        websocket: WebSocket, 
        client_id: str,
        channels: List[str] = None
    ):
        """클라이언트 연결"""
        await websocket.accept()
        
        self.active_connections[client_id] = websocket
        self.metadata[client_id] = {
            "connected_at": datetime.now().isoformat(),
            "channels": channels or ["all"],
            "message_count": 0
        }
        
        # 채널 구독
        subscribe_channels = channels or ["all"]
        for channel in subscribe_channels:
            if channel not in self.channels:
                self.channels[channel] = set()
            self.channels[channel].add(client_id)
        
        self.stats["total_connections"] += 1
        
        # 연결 성공 메시지
        await self.send_personal(client_id, Message(
            type="connected",
            data={
                "client_id": client_id,
                "channels": subscribe_channels,
                "server_time": datetime.now().isoformat()
            }
        ))
        
        # 큐에 있는 메시지 전송
        if client_id in self.message_queue:
            for msg in self.message_queue[client_id]:
                await self.send_personal(client_id, msg)
            del self.message_queue[client_id]
        
        print(f"✅ WebSocket 연결: {client_id} → {subscribe_channels}")
    
    def disconnect(self, client_id: str):
        """클라이언트 연결 해제"""
        if client_id in self.active_connections:
            del self.active_connections[client_id]
        
        # 모든 채널에서 제거
        for channel in self.channels.values():
            channel.discard(client_id)
        
        if client_id in self.metadata:
            del self.metadata[client_id]
        
        print(f"❌ WebSocket 해제: {client_id}")
    
    async def send_personal(self, client_id: str, message: Message):
        """특정 클라이언트에 전송"""
        if client_id in self.active_connections:
            try:
                websocket = self.active_connections[client_id]
                await websocket.send_json(message.dict())
                
                if client_id in self.metadata:
                    self.metadata[client_id]["message_count"] += 1
                
                self.stats["total_messages"] += 1
            except Exception as e:
                print(f"전송 실패 ({client_id}): {e}")
                self.disconnect(client_id)
        else:
            # 연결 없으면 큐에 저장
            if client_id not in self.message_queue:
                self.message_queue[client_id] = []
            self.message_queue[client_id].append(message)
    
    async def broadcast(self, message: Message, channel: str = "all"):
        """채널에 브로드캐스트"""
        if channel not in self.channels:
            return
        
        # 통계
        if channel not in self.stats["messages_per_channel"]:
            self.stats["messages_per_channel"][channel] = 0
        self.stats["messages_per_channel"][channel] += 1
        
        # 채널 구독자들에게 전송
        disconnected = []
        for client_id in self.channels[channel]:
            if client_id in self.active_connections:
                try:
                    websocket = self.active_connections[client_id]
                    await websocket.send_json(message.dict())
                    self.stats["total_messages"] += 1
                except Exception as e:
                    print(f"브로드캐스트 실패 ({client_id}): {e}")
                    disconnected.append(client_id)
        
        # 실패한 연결 정리
        for client_id in disconnected:
            self.disconnect(client_id)
    
    async def broadcast_all(self, message: Message):
        """모든 연결에 브로드캐스트"""
        disconnected = []
        for client_id, websocket in self.active_connections.items():
            try:
                await websocket.send_json(message.dict())
                self.stats["total_messages"] += 1
            except Exception as e:
                print(f"브로드캐스트 실패 ({client_id}): {e}")
                disconnected.append(client_id)
        
        for client_id in disconnected:
            self.disconnect(client_id)
    
    def get_stats(self) -> Dict:
        """통계 반환"""
        return {
            **self.stats,
            "active_connections": len(self.active_connections),
            "channels": {k: len(v) for k, v in self.channels.items()}
        }
    
    def get_clients(self) -> List[Dict]:
        """연결된 클라이언트 목록"""
        return [
            {
                "client_id": cid,
                **self.metadata.get(cid, {})
            }
            for cid in self.active_connections.keys()
        ]


# 글로벌 매니저 인스턴스
manager = ConnectionManager()


# ═══════════════════════════════════════════════════════════════
# 편의 함수 (다른 모듈에서 import하여 사용)
# ═══════════════════════════════════════════════════════════════

async def broadcast_node_update(node_id: str, value: float, source: str = "webhook"):
    """노드 업데이트 브로드캐스트"""
    await manager.broadcast(
        Message(
            type="node_update",
            data={
                "node_id": node_id,
                "value": value,
                "source": source,
                "action": "pulse"  # 프론트엔드에서 펄스 애니메이션
            }
        ),
        channel="physics-map"
    )


async def broadcast_motion_update(source_id: str, target_id: str, amount: float):
    """모션(엣지) 업데이트 브로드캐스트"""
    await manager.broadcast(
        Message(
            type="motion_update",
            data={
                "source": source_id,
                "target": target_id,
                "amount": amount,
                "action": "flow"  # 프론트엔드에서 흐름 애니메이션
            }
        ),
        channel="physics-map"
    )


async def broadcast_synergy_update(synergy: float, total_value: float):
    """시너지 업데이트 브로드캐스트"""
    await manager.broadcast(
        Message(
            type="synergy_update",
            data={
                "synergy": synergy,
                "total_value": total_value
            }
        ),
        channel="physics-map"
    )


async def broadcast_flywheel_pulse(stage: str, momentum: float):
    """플라이휠 펄스 브로드캐스트"""
    await manager.broadcast(
        Message(
            type="flywheel_pulse",
            data={
                "stage": stage,  # delete, automate, synergy, accelerate
                "momentum": momentum
            }
        ),
        channel="flywheel"
    )


async def broadcast_webhook_received(source: str, event_type: str, amount: float):
    """Webhook 수신 브로드캐스트 (대시보드용)"""
    await manager.broadcast(
        Message(
            type="webhook_received",
            data={
                "source": source,
                "event_type": event_type,
                "amount": amount
            }
        ),
        channel="dashboard"
    )



