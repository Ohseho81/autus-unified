# tests/test_websocket.py
# WebSocket 테스트

import pytest
import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from websocket.manager import (
    ConnectionManager,
    Message,
    broadcast_node_update,
    broadcast_motion_update,
    broadcast_synergy_update
)


class TestMessage:
    """Message 클래스 테스트"""
    
    def test_message_creation(self):
        """메시지 생성"""
        msg = Message(type="test", data={"key": "value"})
        
        assert msg.type == "test"
        assert msg.data["key"] == "value"
        assert msg.timestamp is not None
    
    def test_message_auto_timestamp(self):
        """자동 타임스탬프"""
        msg = Message(type="test", data={})
        
        assert msg.timestamp is not None
        assert "2026" in msg.timestamp  # 현재 년도


class TestConnectionManager:
    """ConnectionManager 테스트"""
    
    def setup_method(self):
        self.manager = ConnectionManager()
    
    def test_initial_state(self):
        """초기 상태"""
        assert len(self.manager.active_connections) == 0
        assert "physics-map" in self.manager.channels
        assert "dashboard" in self.manager.channels
        assert "flywheel" in self.manager.channels
        assert "all" in self.manager.channels
    
    def test_disconnect_nonexistent(self):
        """존재하지 않는 클라이언트 해제"""
        # 에러 없이 처리되어야 함
        self.manager.disconnect("nonexistent_client")
        assert len(self.manager.active_connections) == 0
    
    def test_get_stats(self):
        """통계 조회"""
        stats = self.manager.get_stats()
        
        assert "total_connections" in stats
        assert "total_messages" in stats
        assert "active_connections" in stats
        assert "channels" in stats
    
    def test_get_clients_empty(self):
        """빈 클라이언트 목록"""
        clients = self.manager.get_clients()
        assert clients == []


class TestBroadcastFunctions:
    """브로드캐스트 함수 테스트"""
    
    @pytest.mark.asyncio
    async def test_broadcast_node_update(self):
        """노드 업데이트 브로드캐스트"""
        # 연결 없이도 에러 없이 실행되어야 함
        await broadcast_node_update("node_123", 50000, "stripe")
    
    @pytest.mark.asyncio
    async def test_broadcast_motion_update(self):
        """모션 업데이트 브로드캐스트"""
        await broadcast_motion_update("node_001", "node_002", 10000)
    
    @pytest.mark.asyncio
    async def test_broadcast_synergy_update(self):
        """시너지 업데이트 브로드캐스트"""
        await broadcast_synergy_update(1.5, 1000000)


class TestWebSocketAPI:
    """WebSocket HTTP API 테스트"""
    
    def test_stats_endpoint(self):
        """통계 엔드포인트"""
        from fastapi.testclient import TestClient
        from main import app
        
        client = TestClient(app)
        response = client.get("/websocket/stats")
        
        assert response.status_code == 200
        data = response.json()
        assert "active_connections" in data
        assert "total_messages" in data
    
    def test_clients_endpoint(self):
        """클라이언트 목록 엔드포인트"""
        from fastapi.testclient import TestClient
        from main import app
        
        client = TestClient(app)
        response = client.get("/websocket/clients")
        
        assert response.status_code == 200
        data = response.json()
        assert "clients" in data
        assert "count" in data
    
    def test_broadcast_test_endpoint(self):
        """테스트 브로드캐스트 엔드포인트"""
        from fastapi.testclient import TestClient
        from main import app
        
        client = TestClient(app)
        response = client.post(
            "/websocket/broadcast/test",
            params={"node_id": "test_node", "value": 100000}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
    
    def test_broadcast_motion_endpoint(self):
        """모션 브로드캐스트 엔드포인트"""
        from fastapi.testclient import TestClient
        from main import app
        
        client = TestClient(app)
        response = client.post(
            "/websocket/broadcast/motion",
            params={
                "source": "node_001",
                "target": "node_002",
                "amount": 50000
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
    
    def test_broadcast_synergy_endpoint(self):
        """시너지 브로드캐스트 엔드포인트"""
        from fastapi.testclient import TestClient
        from main import app
        
        client = TestClient(app)
        response = client.post(
            "/websocket/broadcast/synergy",
            params={"synergy": 1.5, "total_value": 1000000}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
