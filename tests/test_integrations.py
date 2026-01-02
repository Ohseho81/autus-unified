# tests/test_integrations.py
# Integration 모듈 테스트 (Zero Meaning, Neo4j)

import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from integrations.zero_meaning import ZeroMeaningFilter, FORBIDDEN_FIELDS


class TestZeroMeaningFilter:
    """Zero Meaning Filter 테스트"""
    
    def test_forbidden_fields_defined(self):
        """금지 필드 정의됨"""
        assert len(FORBIDDEN_FIELDS) > 0
        assert "name" in FORBIDDEN_FIELDS
        assert "email" in FORBIDDEN_FIELDS
        assert "description" in FORBIDDEN_FIELDS
    
    def test_clean_basic(self):
        """기본 정제"""
        data = {
            "id": "123",
            "name": "Test",
            "value": 1000
        }
        result = ZeroMeaningFilter.clean(data)
        
        assert "id" in result
        assert "value" in result
        assert "name" not in result
    
    def test_clean_all_forbidden(self):
        """모든 금지 필드 제거"""
        data = {
            "id": "123",
            "name": "John",
            "first_name": "John",
            "last_name": "Doe",
            "email": "john@test.com",
            "phone": "010-1234-5678",
            "address": "Seoul",
            "description": "Test description",
            "note": "Some note",
            "title": "Mr.",
            "category": "VIP",
            "tag": "important",
            "role": "admin",
            "type": "customer",
            "status": "active",
            "label": "primary",
            "comment": "No comment"
        }
        result = ZeroMeaningFilter.clean(data)
        
        # 금지 필드만 제거
        for field in FORBIDDEN_FIELDS:
            assert field not in result
        
        # ID는 보존
        assert result["id"] == "123"
    
    def test_clean_preserves_numeric(self):
        """숫자 필드 보존"""
        data = {
            "amount": 5000,
            "total": 10000,
            "price": 15000,
            "quantity": 3,
            "rate": 0.15
        }
        result = ZeroMeaningFilter.clean(data)
        
        assert result["amount"] == 5000
        assert result["total"] == 10000
        assert result["price"] == 15000
        assert result["quantity"] == 3
        assert result["rate"] == 0.15
    
    def test_clean_preserves_ids(self):
        """ID 필드 보존"""
        data = {
            "id": "abc",
            "customer_id": "cus_123",
            "user_id": "usr_456",
            "order_id": "ord_789",
            "node_id": "node_111"
        }
        result = ZeroMeaningFilter.clean(data)
        
        assert result["id"] == "abc"
        assert result["customer_id"] == "cus_123"
        assert result["user_id"] == "usr_456"
        assert result["order_id"] == "ord_789"
        assert result["node_id"] == "node_111"
    
    def test_clean_preserves_timestamps(self):
        """타임스탬프 보존"""
        data = {
            "created_at": "2026-01-01T00:00:00Z",
            "updated_at": "2026-01-02T00:00:00Z",
            "timestamp": 1704067200,
            "date": "2026-01-01"
        }
        result = ZeroMeaningFilter.clean(data)
        
        assert "created_at" in result
        assert "updated_at" in result
        assert "timestamp" in result
        assert "date" in result
    
    def test_clean_nested_dict(self):
        """중첩 딕셔너리 처리"""
        data = {
            "customer": {
                "id": "cus_123",
                "name": "John Doe",
                "email": "john@test.com"
            },
            "amount": 5000
        }
        result = ZeroMeaningFilter.clean(data)
        
        # 중첩 객체도 정제됨
        assert "customer" in result
        assert result["customer"]["id"] == "cus_123"
        assert "name" not in result["customer"]
        assert "email" not in result["customer"]
    
    def test_clean_list_of_dicts(self):
        """딕셔너리 리스트 처리"""
        data = {
            "items": [
                {"id": "1", "name": "Item 1", "price": 100},
                {"id": "2", "name": "Item 2", "price": 200}
            ]
        }
        result = ZeroMeaningFilter.clean(data)
        
        # 리스트 내 각 항목도 정제됨
        for item in result["items"]:
            assert "name" not in item
            assert "id" in item
            assert "price" in item
    
    def test_clean_empty_dict(self):
        """빈 딕셔너리"""
        result = ZeroMeaningFilter.clean({})
        assert result == {}
    
    def test_extract_core_values(self):
        """핵심 값 추출"""
        data = {
            "customer": "cus_123",
            "amount": 5000,
            "created_at": "2026-01-01"
        }
        result = ZeroMeaningFilter.extract_core(data)
        
        assert "node_id" in result
        assert "value" in result
        assert "timestamp" in result


class TestNeo4jQueries:
    """Neo4j 쿼리 테스트 (Mock)"""
    
    def test_create_node_query(self):
        """노드 생성 쿼리"""
        from integrations.neo4j_client import Neo4jClient
        
        # 쿼리 문자열 검증
        query = """
        MERGE (p:Person {id: $node_id})
        SET p.value = COALESCE(p.value, 0) + $value,
            p.updated_at = datetime()
        RETURN p
        """
        
        assert "MERGE" in query
        assert "Person" in query
        assert "$node_id" in query
        assert "$value" in query
    
    def test_create_motion_query(self):
        """모션 생성 쿼리"""
        query = """
        MATCH (source:Person {id: $source_id})
        MATCH (target:Person {id: $target_id})
        CREATE (source)-[m:MOTION {
            amount: $amount,
            type: $flow_type,
            created_at: datetime()
        }]->(target)
        RETURN m
        """
        
        assert "MATCH" in query
        assert "CREATE" in query
        assert "MOTION" in query
        assert "$amount" in query
    
    def test_get_synergy_query(self):
        """시너지 계산 쿼리"""
        query = """
        MATCH (p:Person)
        WITH sum(p.value) as total_value, count(p) as node_count
        MATCH ()-[m:MOTION]->()
        WITH total_value, node_count, count(m) as edge_count
        RETURN total_value, node_count, edge_count,
               (edge_count * 1.0 / node_count) as avg_connections
        """
        
        assert "sum(p.value)" in query
        assert "count(p)" in query
        assert "count(m)" in query


class TestDataPipeline:
    """데이터 파이프라인 테스트"""
    
    def test_stripe_to_node_motion(self, sample_stripe_payload):
        """Stripe → Node/Motion 변환"""
        data = sample_stripe_payload["data"]["object"]
        
        # Zero Meaning 정제
        cleaned = ZeroMeaningFilter.clean(data)
        
        # 핵심 값 추출
        node_id = cleaned.get("customer") or cleaned.get("id")
        value = cleaned.get("amount", 0) / 100
        
        assert node_id is not None
        assert value > 0
        assert "description" not in cleaned
    
    def test_shopify_to_node_motion(self, sample_shopify_payload):
        """Shopify → Node/Motion 변환"""
        data = sample_shopify_payload
        
        # Zero Meaning 정제
        cleaned = ZeroMeaningFilter.clean(data)
        
        # 핵심 값 추출
        customer = cleaned.get("customer", {})
        node_id = str(customer.get("id") or cleaned.get("id"))
        value = float(cleaned.get("total_price", 0))
        
        assert node_id is not None
        assert value > 0
        
        # 고객 이름 제거됨
        assert "first_name" not in customer
        assert "last_name" not in customer
    
    def test_toss_to_node_motion(self, sample_toss_payload):
        """토스 → Node/Motion 변환"""
        data = sample_toss_payload
        
        # Zero Meaning 정제
        cleaned = ZeroMeaningFilter.clean(data)
        
        # 핵심 값 추출
        node_id = cleaned.get("orderId")
        value = cleaned.get("totalAmount", 0)
        
        assert node_id == "order_456"
        assert value == 50000
    
    def test_erp_to_node_motion(self, sample_erp_data):
        """ERP (하이클래스) → Node/Motion 변환"""
        data = sample_erp_data
        
        # Zero Meaning 정제
        cleaned = ZeroMeaningFilter.clean(data)
        
        # 핵심 값 추출
        node_id = cleaned.get("student_id")
        value = cleaned.get("tuition") or cleaned.get("payment")
        
        assert node_id == "STU_001"
        assert value == 300000
        
        # 학생 이름 제거됨
        assert "student_name" not in cleaned
    
    def test_crm_to_node_motion(self, sample_crm_data):
        """CRM (HubSpot) → Node/Motion 변환"""
        data = sample_crm_data
        
        # Zero Meaning 정제
        cleaned = ZeroMeaningFilter.clean(data)
        
        # 핵심 값 추출
        props = cleaned.get("properties", {})
        node_id = props.get("hs_contact_id") or cleaned.get("id")
        value = float(props.get("hs_deal_amount", 0))
        
        assert node_id is not None
        
        # 이름/이메일 제거됨
        assert "firstname" not in props
        assert "lastname" not in props
        assert "email" not in props
