# tests/test_autosync.py
# AutoSync 모듈 테스트

import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from autosync.detector import AutoSyncDetector
from autosync.transformer import UniversalTransformer, FlowTypeDetector
from autosync.registry import SaaSRegistry, SystemType


class TestSaaSRegistry:
    """SaaS Registry 테스트"""
    
    def test_registry_has_systems(self):
        """시스템 목록이 있는지"""
        systems = SaaSRegistry.get_all()
        assert len(systems) > 0
        assert len(systems) >= 15  # 최소 15개 이상
    
    def test_get_by_type_payment(self):
        """결제 시스템 필터"""
        payment = SaaSRegistry.get_by_type(SystemType.PAYMENT)
        assert "stripe" in payment
        assert "toss" in payment
    
    def test_get_by_type_erp(self):
        """ERP 시스템 필터"""
        erp = SaaSRegistry.get_by_type(SystemType.ERP)
        assert "highclass" in erp
    
    def test_get_by_type_crm(self):
        """CRM 시스템 필터"""
        crm = SaaSRegistry.get_by_type(SystemType.CRM)
        assert "hubspot" in crm
    
    def test_get_mapping(self):
        """매핑 조회"""
        mapping = SaaSRegistry.get_mapping("stripe")
        assert mapping is not None
        assert "node_id" in mapping
        assert "value" in mapping
    
    def test_get_mapping_unknown(self):
        """존재하지 않는 시스템"""
        mapping = SaaSRegistry.get_mapping("unknown_system")
        assert mapping is None


class TestAutoSyncDetector:
    """AutoSync 감지기 테스트"""
    
    def setup_method(self):
        self.detector = AutoSyncDetector()
    
    def test_detect_from_cookies_stripe(self):
        """Stripe 쿠키 감지"""
        cookies = "__stripe_mid=abc123; __stripe_sid=def456"
        detected = self.detector.detect_from_cookies(cookies)
        assert "stripe" in detected
    
    def test_detect_from_cookies_hubspot(self):
        """HubSpot 쿠키 감지"""
        cookies = "hubspotutk=abc123; __hstc=def456"
        detected = self.detector.detect_from_cookies(cookies)
        assert "hubspot" in detected
    
    def test_detect_from_cookies_multiple(self):
        """여러 시스템 동시 감지"""
        cookies = "__stripe_mid=abc; hubspotutk=def"
        detected = self.detector.detect_from_cookies(cookies)
        assert "stripe" in detected
        assert "hubspot" in detected
    
    def test_detect_from_domains_stripe(self):
        """Stripe 도메인 감지"""
        domains = ["stripe.com", "js.stripe.com", "google.com"]
        detected = self.detector.detect_from_domains(domains)
        assert "stripe" in detected
    
    def test_detect_from_domains_class101(self):
        """클래스101 도메인 감지"""
        domains = ["class101.net", "api.class101.net"]
        detected = self.detector.detect_from_domains(domains)
        assert "class101" in detected
    
    def test_detect_from_api_key_stripe(self):
        """Stripe API 키 감지"""
        detected = self.detector.detect_from_api_key("sk_live_abc123")
        assert detected == "stripe"
    
    def test_detect_from_api_key_toss(self):
        """토스 API 키 감지"""
        detected = self.detector.detect_from_api_key("live_sk_abc123")
        assert detected == "toss"
    
    def test_detect_from_api_key_unknown(self):
        """알 수 없는 API 키"""
        detected = self.detector.detect_from_api_key("unknown_key_123")
        assert detected is None
    
    def test_detect_all_combined(self):
        """통합 감지"""
        result = self.detector.detect_all(
            cookies="__stripe_mid=abc",
            domains=["hubspot.com"],
            api_key="live_sk_xyz"
        )
        assert result["count"] >= 2
        assert "stripe" in result["detected"]
        assert "hubspot" in result["detected"]
    
    def test_detect_all_empty(self):
        """빈 입력"""
        result = self.detector.detect_all()
        assert result["count"] == 0
        assert result["detected"] == []


class TestUniversalTransformer:
    """Universal Transformer 테스트"""
    
    def setup_method(self):
        self.transformer = UniversalTransformer()
    
    def test_transform_stripe(self):
        """Stripe 데이터 변환"""
        data = {
            "customer": "cus_123",
            "amount": 5000,
            "created": "2026-01-02T00:00:00Z"
        }
        result = self.transformer.transform(data, "stripe")
        
        assert result["node_id"] == "cus_123"
        assert result["value"] == 50.0  # cents → dollars (/ 100)
        assert result["source"] == "stripe"
    
    def test_transform_toss(self):
        """토스 데이터 변환"""
        data = {
            "orderId": "order_456",
            "totalAmount": 50000,
            "approvedAt": "2026-01-02T00:00:00+09:00"
        }
        result = self.transformer.transform(data, "toss")
        
        assert result["node_id"] == "order_456"
        assert result["value"] == 50000.0
        assert result["source"] == "toss"
    
    def test_transform_hubspot(self, sample_crm_data):
        """HubSpot 데이터 변환"""
        result = self.transformer.transform(sample_crm_data, "hubspot")
        
        assert result["node_id"] == "456"  # properties.hs_contact_id
        assert result["source"] == "hubspot"
    
    def test_transform_highclass(self, sample_erp_data):
        """하이클래스 데이터 변환"""
        result = self.transformer.transform(sample_erp_data, "highclass")
        
        assert result["node_id"] == "STU_001"
        assert result["value"] == 300000.0
        assert result["source"] == "highclass"
    
    def test_transform_unknown_system(self):
        """알 수 없는 시스템 - 범용 변환"""
        data = {
            "id": "generic_123",
            "amount": 10000,
            "timestamp": "2026-01-02"
        }
        result = self.transformer.transform(data, "unknown_system")
        
        assert result["node_id"] == "generic_123"
        assert result["value"] == 10000.0
        assert result["source"] == "unknown"
    
    def test_transform_generic_fallback(self):
        """매핑 없을 때 범용 추출"""
        data = {
            "customer_id": "fallback_123",
            "total": 25000
        }
        result = self.transformer.transform(data, None)
        
        assert result["node_id"] == "fallback_123"
        assert result["value"] == 25000.0


class TestFlowTypeDetector:
    """Flow Type Detector 테스트"""
    
    def test_detect_inflow_succeeded(self):
        """결제 성공 = inflow"""
        data = {"type": "payment_intent.succeeded"}
        assert FlowTypeDetector.detect(data) == "inflow"
    
    def test_detect_inflow_paid(self):
        """결제 완료 = inflow"""
        data = {"event": "order.paid"}
        assert FlowTypeDetector.detect(data) == "inflow"
    
    def test_detect_outflow_refund(self):
        """환불 = outflow"""
        data = {"type": "charge.refunded"}
        assert FlowTypeDetector.detect(data) == "outflow"
    
    def test_detect_outflow_cancel(self):
        """취소 = outflow"""
        data = {"status": "CANCELED"}
        assert FlowTypeDetector.detect(data) == "outflow"
    
    def test_detect_outflow_chargeback(self):
        """차지백 = outflow"""
        data = {"event": "dispute.chargeback"}
        assert FlowTypeDetector.detect(data) == "outflow"
    
    def test_detect_default_inflow(self):
        """기본값 = inflow"""
        data = {"status": "DONE"}
        assert FlowTypeDetector.detect(data) == "inflow"
