# tests/test_crewai.py
# CrewAI 모듈 테스트

import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from crewai.agents import rule_based_analysis, create_summary


class TestRuleBasedAnalysis:
    """규칙 기반 분석 테스트 (CrewAI fallback)"""
    
    def test_delete_targets_negative_value(self, sample_nodes, sample_motions):
        """음수 가치 노드 삭제 대상 식별"""
        result = rule_based_analysis(sample_nodes, sample_motions)
        
        assert result["success"] is True
        assert "delete" in result
        
        # node_3 (-10000), node_4 (0) 이 삭제 대상
        delete_ids = [t["id"] for t in result["delete"]["targets"]]
        assert "node_3" in delete_ids
        assert "node_4" in delete_ids
        assert "node_1" not in delete_ids  # 양수 가치
    
    def test_delete_targets_zero_value(self, sample_nodes, sample_motions):
        """0 가치 노드도 삭제 대상"""
        result = rule_based_analysis(sample_nodes, sample_motions)
        
        delete_ids = [t["id"] for t in result["delete"]["targets"]]
        assert "node_4" in delete_ids  # value = 0
    
    def test_automate_targets_frequent_motions(self, sample_nodes, sample_motions):
        """반복 모션 자동화 대상 식별"""
        result = rule_based_analysis(sample_nodes, sample_motions)
        
        assert "automate" in result
        
        # node_1 -> node_2 가 3회 반복
        automate_motions = [t["motion"] for t in result["automate"]["targets"]]
        assert "node_1->node_2" in automate_motions
    
    def test_automate_targets_threshold(self):
        """3회 미만 반복은 자동화 대상 아님"""
        nodes = [{"id": "a", "value": 100}]
        motions = [
            {"source": "a", "target": "b", "amount": 100},
            {"source": "a", "target": "b", "amount": 200}  # 2회만
        ]
        result = rule_based_analysis(nodes, motions)
        
        # 2회는 자동화 대상 아님
        assert len(result["automate"]["targets"]) == 0
    
    def test_outsource_recommendations(self, sample_nodes, sample_motions):
        """외부용역 추천 존재"""
        result = rule_based_analysis(sample_nodes, sample_motions)
        
        assert "outsource" in result
        assert "recommendations" in result["outsource"]
        assert len(result["outsource"]["recommendations"]) > 0
    
    def test_total_monthly_impact(self, sample_nodes, sample_motions):
        """월간 총 효과 계산"""
        result = rule_based_analysis(sample_nodes, sample_motions)
        
        assert "total_monthly_impact" in result
        assert result["total_monthly_impact"] > 0
    
    def test_monthly_savings_calculation(self, sample_nodes, sample_motions):
        """삭제로 인한 월간 절감액"""
        result = rule_based_analysis(sample_nodes, sample_motions)
        
        # 삭제 대상 수 × 500,000원
        delete_count = len(result["delete"]["targets"])
        expected_savings = delete_count * 500000
        assert result["delete"]["monthly_savings"] == expected_savings
    
    def test_empty_nodes(self):
        """빈 노드 리스트"""
        result = rule_based_analysis([], [])
        
        assert result["success"] is True
        assert len(result["delete"]["targets"]) == 0
        assert len(result["automate"]["targets"]) == 0
    
    def test_all_positive_nodes(self):
        """모두 양수 가치인 경우"""
        nodes = [
            {"id": "a", "value": 100000},
            {"id": "b", "value": 200000}
        ]
        result = rule_based_analysis(nodes, [])
        
        # 삭제 대상 없음
        assert len(result["delete"]["targets"]) == 0


class TestCreateSummary:
    """LLM용 요약 생성 테스트"""
    
    def test_summary_format(self, sample_nodes, sample_motions):
        """요약 형식 확인"""
        summary = create_summary(sample_nodes, sample_motions)
        
        assert "노드" in summary
        assert "5개" in summary  # 5개 노드
        assert "가치" in summary
        assert "저가치" in summary
    
    def test_summary_total_value(self, sample_nodes, sample_motions):
        """총 가치 계산"""
        summary = create_summary(sample_nodes, sample_motions)
        
        # 100000 + 50000 - 10000 + 0 + 200000 = 340000
        assert "340,000" in summary
    
    def test_summary_low_value_count(self, sample_nodes, sample_motions):
        """저가치 노드 수"""
        summary = create_summary(sample_nodes, sample_motions)
        
        # node_3 (-10000), node_4 (0) = 2개
        assert "2개" in summary
    
    def test_summary_empty(self):
        """빈 데이터"""
        summary = create_summary([], [])
        
        assert "노드 0개" in summary
        assert "₩0" in summary


class TestCrewAIIntegration:
    """CrewAI 통합 테스트 (Mock)"""
    
    def test_analyze_returns_result(self, sample_nodes, sample_motions):
        """분석 결과 반환"""
        # CrewAI 없으면 rule_based_analysis로 fallback
        result = rule_based_analysis(sample_nodes, sample_motions)
        
        assert "success" in result
        assert "delete" in result
        assert "automate" in result
        assert "outsource" in result
    
    def test_result_structure(self, sample_nodes, sample_motions):
        """결과 구조 검증"""
        result = rule_based_analysis(sample_nodes, sample_motions)
        
        # delete 구조
        assert "targets" in result["delete"]
        assert "monthly_savings" in result["delete"]
        
        # automate 구조
        assert "targets" in result["automate"]
        assert "monthly_synergy_gain" in result["automate"]
        
        # outsource 구조
        assert "recommendations" in result["outsource"]
        assert "monthly_acceleration" in result["outsource"]
