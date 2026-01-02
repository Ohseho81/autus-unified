# tests/test_api.py
# FastAPI 엔드포인트 테스트

import pytest
from fastapi.testclient import TestClient
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from main import app

client = TestClient(app)


class TestHealthEndpoint:
    """Health Check 테스트"""
    
    def test_health_check(self):
        """헬스 체크"""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"
    
    def test_root_endpoint(self):
        """루트 엔드포인트"""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "name" in data
        assert "AUTUS" in data["name"]
    
    def test_strategy_endpoint(self):
        """전략 엔드포인트"""
        response = client.get("/strategy")
        assert response.status_code == 200
        data = response.json()
        assert "core_strategies" in data
        assert "projected_roi" in data


class TestAutoSyncAPI:
    """AutoSync API 테스트"""
    
    def test_list_systems(self):
        """시스템 목록"""
        response = client.get("/autosync/systems")
        assert response.status_code == 200
        data = response.json()
        assert "total" in data
        assert data["total"] >= 15
    
    def test_detect_from_cookies(self):
        """쿠키로 감지"""
        response = client.post("/autosync/detect", json={
            "cookies": "__stripe_mid=abc123"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "stripe" in data["detected"]
    
    def test_detect_from_domains(self):
        """도메인으로 감지"""
        response = client.post("/autosync/detect", json={
            "domains": ["hubspot.com", "api.hubapi.com"]
        })
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "hubspot" in data["detected"]
    
    def test_detect_from_api_key(self):
        """API 키로 감지"""
        response = client.post("/autosync/detect", json={
            "api_key": "sk_live_abc123"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "stripe" in data["detected"]
    
    def test_detect_combined(self):
        """통합 감지"""
        response = client.post("/autosync/detect", json={
            "cookies": "__stripe_mid=abc",
            "domains": ["hubspot.com"],
            "api_key": "live_sk_xyz"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["count"] >= 2
    
    def test_transform_stripe(self):
        """Stripe 데이터 변환"""
        response = client.post("/autosync/transform", json={
            "data": {
                "customer": "cus_123",
                "amount": 5000
            },
            "system_id": "stripe"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["transformed"]["node_id"] == "cus_123"
        assert data["transformed"]["value"] == 50.0
    
    def test_transform_toss(self):
        """토스 데이터 변환"""
        response = client.post("/autosync/transform", json={
            "data": {
                "orderId": "order_123",
                "totalAmount": 50000
            },
            "system_id": "toss"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["transformed"]["node_id"] == "order_123"
        assert data["transformed"]["value"] == 50000.0
    
    def test_connect_system(self):
        """시스템 연결"""
        response = client.post("/autosync/connect?system_id=stripe")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "webhook_url" in data


class TestCrewAIAPI:
    """CrewAI API 테스트"""
    
    def test_analyze(self):
        """분석 실행"""
        response = client.post("/crewai/analyze", json={
            "nodes": [
                {"id": "node_1", "value": 100000},
                {"id": "node_2", "value": -10000}
            ],
            "motions": [
                {"source": "node_1", "target": "node_2", "amount": 5000}
            ]
        })
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "delete" in data
        assert "automate" in data
    
    def test_quick_delete(self):
        """빠른 삭제 분석"""
        response = client.post("/crewai/quick-delete", json={
            "nodes": [
                {"id": "a", "value": 100},
                {"id": "b", "value": -50},
                {"id": "c", "value": 0}
            ],
            "motions": []
        })
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["count"] == 2  # b와 c
    
    def test_quick_automate(self):
        """빠른 자동화 분석"""
        response = client.post("/crewai/quick-automate", json={
            "nodes": [],
            "motions": [
                {"source": "a", "target": "b", "amount": 100},
                {"source": "a", "target": "b", "amount": 200},
                {"source": "a", "target": "b", "amount": 300}
            ]
        })
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["count"] == 1  # a->b 3회 반복
    
    def test_health(self):
        """CrewAI 헬스 체크"""
        response = client.get("/crewai/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"


class TestParasiticAPI:
    """Parasitic API 테스트"""
    
    def test_list_supported(self):
        """지원 시스템 목록"""
        response = client.get("/parasitic/supported")
        assert response.status_code == 200
        data = response.json()
        assert "supported" in data
        assert len(data["supported"]) >= 5
    
    def test_connect(self):
        """연동 시작"""
        response = client.post("/parasitic/connect", json={
            "saas_type": "toss_pos"
        })
        assert response.status_code == 200
        data = response.json()
        assert "connector_id" in data
        assert data["success"] is True
    
    def test_status(self):
        """상태 조회"""
        # 먼저 연결
        client.post("/parasitic/connect", json={"saas_type": "toss_pos"})
        
        response = client.get("/parasitic/status")
        assert response.status_code == 200
        data = response.json()
        assert "connectors" in data
        assert "total" in data
    
    def test_flywheel(self):
        """플라이휠 상태"""
        response = client.get("/parasitic/flywheel")
        assert response.status_code == 200
        data = response.json()
        assert "total" in data
        assert "replaced" in data
        assert "monthly_savings" in data


class TestPhysicsAPI:
    """Physics Engine API 테스트"""
    
    def test_physics_state(self):
        """물리 엔진 상태"""
        response = client.get("/physics/state")
        assert response.status_code == 200
        data = response.json()
        assert "nodes" in data
        assert "total_value" in data
        assert "synergy" in data
    
    def test_physics_kpi(self):
        """KPI 조회"""
        response = client.get("/physics/kpi")
        assert response.status_code == 200
        data = response.json()
        assert "total_mint" in data
        assert "total_burn" in data
        assert "synergy" in data
    
    def test_physics_predict(self):
        """예측"""
        response = client.get("/physics/predict")
        assert response.status_code == 200
        data = response.json()
        assert "predicted_mint" in data
        assert "confidence" in data
    
    def test_physics_event(self):
        """이벤트 추가"""
        response = client.post("/physics/event", json={
            "event_type": "mint",
            "amount": 1000000,
            "minutes": 60,
            "participants": ["P01"]
        })
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "event_id" in data


class TestWebhookAPI:
    """Webhook API 테스트"""
    
    def test_universal_webhook(self):
        """범용 Webhook"""
        response = client.post("/webhook/universal", json={
            "type": "test",
            "data": {
                "customer": "cus_123",
                "amount": 1000
            }
        })
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "transformed" in data
    
    def test_stripe_webhook_no_signature(self):
        """Stripe Webhook (시그니처 없음 - 테스트 모드)"""
        response = client.post(
            "/webhook/stripe",
            json={
                "type": "payment_intent.succeeded",
                "data": {
                    "object": {
                        "customer": "cus_test",
                        "amount": 5000
                    }
                }
            }
        )
        # 시그니처 검증 실패하지만 테스트 환경에서는 처리
        assert response.status_code in [200, 400]


class TestAPIValidation:
    """API 입력 검증 테스트"""
    
    def test_detect_empty_request(self):
        """빈 요청 처리"""
        response = client.post("/autosync/detect", json={})
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 0
    
    def test_transform_missing_data(self):
        """데이터 누락"""
        response = client.post("/autosync/transform", json={
            "system_id": "stripe"
        })
        assert response.status_code == 422  # Validation Error
    
    def test_analyze_empty_nodes(self):
        """빈 노드 리스트"""
        response = client.post("/crewai/analyze", json={
            "nodes": [],
            "motions": []
        })
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True


class TestWebSocketAPI:
    """WebSocket HTTP API 테스트"""
    
    def test_websocket_stats(self):
        """WebSocket 통계"""
        response = client.get("/websocket/stats")
        assert response.status_code == 200
        data = response.json()
        assert "total_connections" in data or "active_connections" in data
    
    def test_websocket_broadcast_test(self):
        """테스트 브로드캐스트"""
        response = client.post("/websocket/broadcast/test?node_id=test_node&value=100000")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

