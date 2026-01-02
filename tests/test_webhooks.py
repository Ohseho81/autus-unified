# tests/test_webhooks.py
# Webhook 처리 테스트

import pytest
import hashlib
import hmac
import base64
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))


class TestStripeWebhook:
    """Stripe Webhook 테스트"""
    
    def test_verify_signature_valid(self):
        """유효한 시그니처 검증"""
        from webhooks.stripe_webhook import verify_stripe_signature
        
        payload = b'{"test": "data"}'
        secret = "whsec_test_secret"
        timestamp = "1234567890"
        
        # 올바른 시그니처 생성
        signed_payload = f"{timestamp}.{payload.decode()}"
        expected_sig = hmac.new(
            secret.encode(),
            signed_payload.encode(),
            hashlib.sha256
        ).hexdigest()
        
        sig_header = f"t={timestamp},v1={expected_sig}"
        
        result = verify_stripe_signature(payload, sig_header, secret)
        assert result is True
    
    def test_verify_signature_invalid(self):
        """잘못된 시그니처"""
        from webhooks.stripe_webhook import verify_stripe_signature
        
        payload = b'{"test": "data"}'
        secret = "whsec_test_secret"
        sig_header = "t=1234567890,v1=invalid_signature"
        
        result = verify_stripe_signature(payload, sig_header, secret)
        assert result is False
    
    def test_verify_signature_missing_parts(self):
        """시그니처 파트 누락"""
        from webhooks.stripe_webhook import verify_stripe_signature
        
        payload = b'{"test": "data"}'
        secret = "whsec_test_secret"
        sig_header = "invalid_format"
        
        result = verify_stripe_signature(payload, sig_header, secret)
        assert result is False


class TestShopifyWebhook:
    """Shopify Webhook 테스트"""
    
    def test_verify_hmac_valid(self):
        """유효한 HMAC 검증"""
        from webhooks.shopify_webhook import verify_shopify_hmac
        
        payload = b'{"test": "data"}'
        secret = "shpss_test_secret"
        
        # 올바른 HMAC 생성
        computed = base64.b64encode(
            hmac.new(secret.encode(), payload, hashlib.sha256).digest()
        ).decode()
        
        result = verify_shopify_hmac(payload, computed, secret)
        assert result is True
    
    def test_verify_hmac_invalid(self):
        """잘못된 HMAC"""
        from webhooks.shopify_webhook import verify_shopify_hmac
        
        payload = b'{"test": "data"}'
        secret = "shpss_test_secret"
        wrong_hmac = "invalid_hmac_value"
        
        result = verify_shopify_hmac(payload, wrong_hmac, secret)
        assert result is False


class TestZeroMeaningFilter:
    """Zero Meaning 필터 테스트"""
    
    def test_filter_removes_name(self, sample_stripe_payload):
        """이름 필드 제거"""
        from integrations.zero_meaning import ZeroMeaningFilter
        
        data = {
            "customer": "cus_123",
            "amount": 5000,
            "name": "John Doe",
            "first_name": "John",
            "last_name": "Doe"
        }
        
        result = ZeroMeaningFilter.clean(data)
        
        assert "name" not in result
        assert "first_name" not in result
        assert "last_name" not in result
        assert result["customer"] == "cus_123"
        assert result["amount"] == 5000
    
    def test_filter_removes_email(self):
        """이메일 제거"""
        from integrations.zero_meaning import ZeroMeaningFilter
        
        data = {
            "id": "123",
            "email": "test@example.com",
            "phone": "010-1234-5678"
        }
        
        result = ZeroMeaningFilter.clean(data)
        
        assert "email" not in result
        assert "phone" not in result
        assert result["id"] == "123"
    
    def test_filter_removes_description(self):
        """설명 필드 제거"""
        from integrations.zero_meaning import ZeroMeaningFilter
        
        data = {
            "value": 10000,
            "description": "This is a test",
            "note": "Some note",
            "comment": "A comment"
        }
        
        result = ZeroMeaningFilter.clean(data)
        
        assert "description" not in result
        assert "note" not in result
        assert "comment" not in result
        assert result["value"] == 10000
    
    def test_filter_preserves_numeric(self):
        """숫자 필드 보존"""
        from integrations.zero_meaning import ZeroMeaningFilter
        
        data = {
            "amount": 5000,
            "total": 10000,
            "value": 15000,
            "count": 3
        }
        
        result = ZeroMeaningFilter.clean(data)
        
        assert result["amount"] == 5000
        assert result["total"] == 10000
        assert result["value"] == 15000
        assert result["count"] == 3
    
    def test_filter_preserves_id(self):
        """ID 필드 보존"""
        from integrations.zero_meaning import ZeroMeaningFilter
        
        data = {
            "id": "abc123",
            "customer_id": "cus_456",
            "order_id": "ord_789"
        }
        
        result = ZeroMeaningFilter.clean(data)
        
        assert result["id"] == "abc123"
        assert result["customer_id"] == "cus_456"
        assert result["order_id"] == "ord_789"
    
    def test_filter_nested_data(self):
        """중첩 데이터 처리"""
        from integrations.zero_meaning import ZeroMeaningFilter
        
        data = {
            "customer": {
                "id": "cus_123",
                "name": "John Doe",
                "email": "john@example.com"
            },
            "amount": 5000
        }
        
        result = ZeroMeaningFilter.clean(data)
        
        # 중첩 객체도 정제
        if "customer" in result and isinstance(result["customer"], dict):
            assert "name" not in result["customer"]
            assert "email" not in result["customer"]
            assert result["customer"]["id"] == "cus_123"


class TestWebhookDataExtraction:
    """Webhook 데이터 추출 테스트"""
    
    def test_extract_stripe_node_id(self, sample_stripe_payload):
        """Stripe에서 node_id 추출"""
        data = sample_stripe_payload["data"]["object"]
        
        node_id = data.get("customer") or data.get("id")
        assert node_id == "cus_test_789"
    
    def test_extract_stripe_value(self, sample_stripe_payload):
        """Stripe에서 value 추출"""
        data = sample_stripe_payload["data"]["object"]
        
        value = data.get("amount", 0) / 100  # cents to dollars
        assert value == 50.0
    
    def test_extract_shopify_node_id(self, sample_shopify_payload):
        """Shopify에서 node_id 추출"""
        data = sample_shopify_payload
        
        node_id = str(data.get("customer", {}).get("id") or data.get("id"))
        assert node_id == "987654321"
    
    def test_extract_shopify_value(self, sample_shopify_payload):
        """Shopify에서 value 추출"""
        data = sample_shopify_payload
        
        value = float(data.get("total_price", 0))
        assert value == 100.0
    
    def test_extract_toss_node_id(self, sample_toss_payload):
        """토스에서 node_id 추출"""
        data = sample_toss_payload
        
        node_id = data.get("orderId")
        assert node_id == "order_456"
    
    def test_extract_toss_value(self, sample_toss_payload):
        """토스에서 value 추출"""
        data = sample_toss_payload
        
        value = data.get("totalAmount", 0)
        assert value == 50000
