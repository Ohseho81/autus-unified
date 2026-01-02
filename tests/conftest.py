# tests/conftest.py
# Pytest 공통 설정 및 Fixtures

import pytest
import sys
import os

# 백엔드 경로 추가
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))


@pytest.fixture
def sample_stripe_payload():
    """Stripe Webhook 샘플 페이로드"""
    return {
        "id": "evt_test_123",
        "type": "payment_intent.succeeded",
        "data": {
            "object": {
                "id": "pi_test_456",
                "customer": "cus_test_789",
                "amount": 5000,
                "currency": "usd",
                "description": "Test payment",
                "metadata": {"order_id": "order_123"}
            }
        }
    }


@pytest.fixture
def sample_shopify_payload():
    """Shopify Webhook 샘플 페이로드"""
    return {
        "id": 123456789,
        "order_number": 1001,
        "customer": {
            "id": 987654321,
            "email": "test@example.com",
            "first_name": "John",
            "last_name": "Doe"
        },
        "total_price": "100.00",
        "currency": "USD",
        "created_at": "2026-01-02T00:00:00Z"
    }


@pytest.fixture
def sample_toss_payload():
    """토스 Webhook 샘플 페이로드"""
    return {
        "paymentKey": "toss_pay_123",
        "orderId": "order_456",
        "status": "DONE",
        "totalAmount": 50000,
        "method": "카드",
        "approvedAt": "2026-01-02T00:00:00+09:00"
    }


@pytest.fixture
def sample_nodes():
    """샘플 노드 데이터"""
    return [
        {"id": "node_1", "value": 100000},
        {"id": "node_2", "value": 50000},
        {"id": "node_3", "value": -10000},
        {"id": "node_4", "value": 0},
        {"id": "node_5", "value": 200000}
    ]


@pytest.fixture
def sample_motions():
    """샘플 모션 데이터"""
    return [
        {"source": "node_1", "target": "node_2", "amount": 10000},
        {"source": "node_1", "target": "node_2", "amount": 15000},
        {"source": "node_2", "target": "node_3", "amount": 5000},
        {"source": "node_1", "target": "node_2", "amount": 20000},
        {"source": "node_3", "target": "node_4", "amount": 3000}
    ]


@pytest.fixture
def sample_erp_data():
    """샘플 ERP 데이터 (하이클래스)"""
    return {
        "student_id": "STU_001",
        "student_name": "홍길동",
        "tuition": 300000,
        "payment": 300000,
        "created_at": "2026-01-02T00:00:00"
    }


@pytest.fixture
def sample_crm_data():
    """샘플 CRM 데이터 (HubSpot)"""
    return {
        "id": "contact_123",
        "properties": {
            "hs_contact_id": "456",
            "hs_deal_amount": "1000000",
            "firstname": "John",
            "lastname": "Doe",
            "email": "john@example.com",
            "createdate": "2026-01-02T00:00:00Z"
        }
    }

# tests/conftest.py
# Pytest 공통 설정 및 Fixtures

import pytest
import sys
import os

# 백엔드 경로 추가
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))


@pytest.fixture
def sample_stripe_payload():
    """Stripe Webhook 샘플 페이로드"""
    return {
        "id": "evt_test_123",
        "type": "payment_intent.succeeded",
        "data": {
            "object": {
                "id": "pi_test_456",
                "customer": "cus_test_789",
                "amount": 5000,
                "currency": "usd",
                "description": "Test payment",
                "metadata": {"order_id": "order_123"}
            }
        }
    }


@pytest.fixture
def sample_shopify_payload():
    """Shopify Webhook 샘플 페이로드"""
    return {
        "id": 123456789,
        "order_number": 1001,
        "customer": {
            "id": 987654321,
            "email": "test@example.com",
            "first_name": "John",
            "last_name": "Doe"
        },
        "total_price": "100.00",
        "currency": "USD",
        "created_at": "2026-01-02T00:00:00Z"
    }


@pytest.fixture
def sample_toss_payload():
    """토스 Webhook 샘플 페이로드"""
    return {
        "paymentKey": "toss_pay_123",
        "orderId": "order_456",
        "status": "DONE",
        "totalAmount": 50000,
        "method": "카드",
        "approvedAt": "2026-01-02T00:00:00+09:00"
    }


@pytest.fixture
def sample_nodes():
    """샘플 노드 데이터"""
    return [
        {"id": "node_1", "value": 100000},
        {"id": "node_2", "value": 50000},
        {"id": "node_3", "value": -10000},
        {"id": "node_4", "value": 0},
        {"id": "node_5", "value": 200000}
    ]


@pytest.fixture
def sample_motions():
    """샘플 모션 데이터"""
    return [
        {"source": "node_1", "target": "node_2", "amount": 10000},
        {"source": "node_1", "target": "node_2", "amount": 15000},
        {"source": "node_2", "target": "node_3", "amount": 5000},
        {"source": "node_1", "target": "node_2", "amount": 20000},
        {"source": "node_3", "target": "node_4", "amount": 3000}
    ]


@pytest.fixture
def sample_erp_data():
    """샘플 ERP 데이터 (하이클래스)"""
    return {
        "student_id": "STU_001",
        "student_name": "홍길동",
        "tuition": 300000,
        "payment": 300000,
        "created_at": "2026-01-02T00:00:00"
    }


@pytest.fixture
def sample_crm_data():
    """샘플 CRM 데이터 (HubSpot)"""
    return {
        "id": "contact_123",
        "properties": {
            "hs_contact_id": "456",
            "hs_deal_amount": "1000000",
            "firstname": "John",
            "lastname": "Doe",
            "email": "john@example.com",
            "createdate": "2026-01-02T00:00:00Z"
        }
    }


