#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
╔═══════════════════════════════════════════════════════════════════════════════════════════╗
║                    🌌 AUTUS Physics Map - Core Calculation Engine                         ║
║                                                                                           ║
║  아우투스 철학: 모든 계산은 돈 하나로 귀결                                                    ║
║                                                                                           ║
║  가치 = 직접 돈 - 시간 비용 + 시너지 돈                                                     ║
║                                                                                           ║
║  물리 법칙 비유:                                                                           ║
║  - 뉴턴 제2법칙: F = ma (직접 돈 = 힘, 시간 = 질량, 시너지 = 가속도)                        ║
║  - 중력 법칙: 시너지 = k × (N1 × N2) / d²                                                  ║
║  - 복리 법칙: 미래 = 현재 × (1 + g)^t                                                      ║
╚═══════════════════════════════════════════════════════════════════════════════════════════╝
"""

import math
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum


# ═══════════════════════════════════════════════════════════════════════════════════════════
# Constants & Configuration
# ═══════════════════════════════════════════════════════════════════════════════════════════

@dataclass
class PhysicsConfig:
    """Physics Map 설정"""
    # 시간당 가치 (HV: Hourly Value)
    hourly_value_krw: float = 100_000  # 10만원/시간
    
    # 시너지 상수 (k: 브랜드 강도)
    synergy_constant_k: float = 0.5  # 0.3 ~ 0.7
    
    # 시너지율 (s: 평균 시너지)
    synergy_rate_s: float = 0.2  # 0.1 ~ 0.3
    
    # 복리율 (r: 시너지 강도)
    compound_rate_r: float = 0.15  # 0.1 ~ 0.3
    
    # 삭제 임계값
    delete_threshold_krw: float = 5_000_000  # 500만원 미만 삭제
    
    # 경고 임계값 배수
    warning_lower_ratio: float = 0.8
    warning_upper_ratio: float = 1.2
    danger_ratio: float = 0.5
    
    # 예측 기간
    forecast_months: int = 12


DEFAULT_CONFIG = PhysicsConfig()


# ═══════════════════════════════════════════════════════════════════════════════════════════
# Data Structures
# ═══════════════════════════════════════════════════════════════════════════════════════════

class NodeStatus(str, Enum):
    """노드 상태"""
    OPTIMAL = "OPTIMAL"      # 최적
    NORMAL = "NORMAL"        # 정상
    WARNING = "WARNING"      # 경고
    DANGER = "DANGER"        # 위험
    DELETE = "DELETE"        # 삭제 대상


@dataclass
class MoneyFlow:
    """돈 흐름"""
    inflow_krw: float = 0.0   # 유입
    outflow_krw: float = 0.0  # 유출
    
    @property
    def direct_money(self) -> float:
        """직접 돈 = 유입 - 유출"""
        return self.inflow_krw - self.outflow_krw


@dataclass
class TimeInvestment:
    """시간 투자"""
    hours: float = 0.0  # 투자 시간 (시간)
    hourly_value: float = 100_000  # 시간당 가치 (원)
    
    @property
    def time_cost(self) -> float:
        """시간 비용 = T × HV"""
        return self.hours * self.hourly_value


@dataclass
class SynergyLink:
    """시너지 연결"""
    node_a: str
    node_b: str
    distance: float = 1.0  # 관계 거리 (1=가까움, 5=멀음)
    strength: float = 0.5  # 연결 강도 (0~1)
    
    @property
    def synergy_weight(self) -> float:
        """시너지 가중치 = 강도 / 거리²"""
        return self.strength / (self.distance ** 2)


@dataclass
class PhysicsNode:
    """Physics Map 노드 (사람/자산)"""
    node_id: str
    name: str
    
    # 돈 흐름
    money: MoneyFlow = field(default_factory=MoneyFlow)
    
    # 시간 투자
    time: TimeInvestment = field(default_factory=TimeInvestment)
    
    # 연결 수 (시너지 계산용)
    connection_count: int = 0
    
    # 계산된 값들
    direct_money_krw: float = 0.0
    time_cost_krw: float = 0.0
    synergy_money_krw: float = 0.0
    total_value_krw: float = 0.0
    
    # 상태
    status: NodeStatus = NodeStatus.NORMAL
    
    def compute_value(self) -> float:
        """노드 가치 = 직접 돈 - 시간 비용 + 시너지 돈"""
        self.direct_money_krw = self.money.direct_money
        self.time_cost_krw = self.time.time_cost
        # 시너지는 별도 계산 후 주입
        self.total_value_krw = self.direct_money_krw - self.time_cost_krw + self.synergy_money_krw
        return self.total_value_krw


@dataclass
class PhysicsResult:
    """Physics Map 계산 결과"""
    # 기본 정보
    calculated_at: datetime = field(default_factory=datetime.now)
    config: PhysicsConfig = field(default_factory=PhysicsConfig)
    
    # 노드들
    nodes: Dict[str, PhysicsNode] = field(default_factory=dict)
    
    # 연결들
    links: List[SynergyLink] = field(default_factory=list)
    
    # 집계
    total_direct_money: float = 0.0
    total_time_cost: float = 0.0
    total_synergy_money: float = 0.0
    total_value: float = 0.0
    
    # 미래 예측
    future_value_12m: float = 0.0
    growth_rate: float = 0.0
    
    # 삭제 대상
    delete_targets: List[str] = field(default_factory=list)
    
    # 최적 구성
    optimal_structure: List[str] = field(default_factory=list)
    optimal_value: float = 0.0


# ═══════════════════════════════════════════════════════════════════════════════════════════
# 수식 1: 직접 돈 (Direct Money)
# ═══════════════════════════════════════════════════════════════════════════════════════════

def compute_direct_money(inflows: List[float], outflows: List[float]) -> float:
    """
    직접 돈 = ∑(유입) - ∑(유출)
    
    예시: 등록금 +800만원, 보너스 -100만원 → 직접 돈 +700만원
    """
    return sum(inflows) - sum(outflows)


# ═══════════════════════════════════════════════════════════════════════════════════════════
# 수식 2: 시간 비용 (Time Cost)
# ═══════════════════════════════════════════════════════════════════════════════════════════

def compute_time_cost(hours: float, hourly_value: float = 100_000) -> float:
    """
    시간 비용 = T × HV
    
    T: 투자 시간 (시간)
    HV: 시간당 가치 (원)
    
    예시: 40시간 × 10만원 = 시간 비용 400만원
    """
    return hours * hourly_value


# ═══════════════════════════════════════════════════════════════════════════════════════════
# 수식 3: 시너지 돈 (Synergy Money) - 중력 법칙
# ═══════════════════════════════════════════════════════════════════════════════════════════

def compute_synergy_gravity(
    n1: int,
    n2: int,
    distance: float = 1.0,
    k: float = 0.5,
    r: float = 0.15,
    t: int = 3,
    base_value: float = 10_000_000  # 기준 가치 1000만원
) -> float:
    """
    시너지 돈 = k × (N1 × N2) / d² × (1 + r)^t × base_value
    
    중력 법칙 비유:
    - k: 상수 (브랜드 강도 0.3~0.7)
    - N1, N2: 연결된 사람 수
    - d: 관계 거리 (1=가까움, 5=멀음)
    - r: 복리율 (시너지 강도 0.1~0.3)
    - t: 기간 (월)
    
    예시: 코치 1명 × 학생 100명 / d=1 × k=0.5 × (1.2)^3 = +1,200만원
    """
    if distance <= 0:
        distance = 1.0
    
    gravity = (n1 * n2) / (distance ** 2)
    compound = (1 + r) ** t
    synergy = k * gravity * compound * base_value / 100  # 스케일 조정
    
    return synergy


def compute_synergy_network(
    edges: int,
    synergy_rate: float = 0.2,
    k: float = 0.5,
    base_value: float = 1_000_000  # 기준 100만원
) -> float:
    """
    시너지 가치 = k × E × s × base_value
    
    E: 엣지(연결) 수
    s: 평균 시너지율 (0.1~0.3)
    
    예시: 연결 50개 × s=0.2 × k=0.5 = +500만원
    """
    return k * edges * synergy_rate * base_value


# ═══════════════════════════════════════════════════════════════════════════════════════════
# 수식 4: 노드 가치 통합
# ═══════════════════════════════════════════════════════════════════════════════════════════

def compute_node_value(
    direct_money: float,
    time_cost: float,
    synergy_money: float
) -> float:
    """
    노드 가치 = 직접 돈 - 시간 비용 + 시너지 돈
    
    뉴턴 제2법칙 F = ma 비유:
    - 직접 돈 = 힘 (Force)
    - 시간 비용 = 질량 저항 (Mass)
    - 시너지 = 가속도 (Acceleration)
    """
    return direct_money - time_cost + synergy_money


# ═══════════════════════════════════════════════════════════════════════════════════════════
# 수식 5: 전체 가치 합계
# ═══════════════════════════════════════════════════════════════════════════════════════════

def compute_total_value(nodes: List[PhysicsNode]) -> float:
    """
    총 가치 = ∑(모든 노드 가치)
    
    Total Value = ∑(Direct_i - Time_i + Synergy_i)
    """
    return sum(n.total_value_krw for n in nodes)


# ═══════════════════════════════════════════════════════════════════════════════════════════
# 수식 6: 미래 예측 (복리 법칙)
# ═══════════════════════════════════════════════════════════════════════════════════════════

def compute_future_value(
    current_value: float,
    growth_rate: float,
    months: int = 12
) -> float:
    """
    미래 돈 = 현재 돈 × (1 + g)^t
    
    복리 법칙:
    - g: 월 성장률
    - t: 기간 (월)
    
    예시: g=0.26 → 12개월 후 +1,400% 증가
    """
    if growth_rate < -1:
        growth_rate = -0.99  # 최대 99% 하락 제한
    
    return current_value * ((1 + growth_rate) ** months)


def compute_growth_rate(
    synergy_increase: float = 0.08,
    delete_savings: float = 0.03,
    external_boost: float = 0.15
) -> float:
    """
    성장률 = (시너지 증가율 + 삭제 절감율 + 외부 가속율)
    
    예시: 0.08 + 0.03 + 0.15 = 0.26 (월 26% 성장)
    """
    return synergy_increase + delete_savings + external_boost


# ═══════════════════════════════════════════════════════════════════════════════════════════
# 수식 7: 삭제 우선순위
# ═══════════════════════════════════════════════════════════════════════════════════════════

def should_delete(value: float, threshold: float = 5_000_000) -> bool:
    """
    삭제 대상 = 가치 < 임계값
    
    예시: +500만원 미만 → 삭제 대상
    """
    return value < threshold


def get_delete_priority(nodes: List[PhysicsNode], threshold: float = 5_000_000) -> List[str]:
    """삭제 우선순위 목록 (가치 낮은 순)"""
    delete_candidates = [n for n in nodes if n.total_value_krw < threshold]
    delete_candidates.sort(key=lambda x: x.total_value_krw)
    return [n.node_id for n in delete_candidates]


# ═══════════════════════════════════════════════════════════════════════════════════════════
# 수식 8: 범위 체크 (경고/위험)
# ═══════════════════════════════════════════════════════════════════════════════════════════

def check_value_range(
    value: float,
    lower: float,
    upper: float,
    config: PhysicsConfig = None
) -> NodeStatus:
    """
    범위 체크:
    - 정상: Value ∈ [Lower, Upper]
    - 경고: Value < Lower × 0.8 or Value > Upper × 1.2
    - 위험: Value < Lower × 0.5
    """
    if config is None:
        config = DEFAULT_CONFIG
    
    if value < lower * config.danger_ratio:
        return NodeStatus.DANGER
    elif value < lower * config.warning_lower_ratio:
        return NodeStatus.WARNING
    elif value > upper * config.warning_upper_ratio:
        return NodeStatus.WARNING
    elif lower <= value <= upper:
        return NodeStatus.OPTIMAL
    else:
        return NodeStatus.NORMAL


# ═══════════════════════════════════════════════════════════════════════════════════════════
# 수식 9: 최고치 판단 (Optimization)
# ═══════════════════════════════════════════════════════════════════════════════════════════

def find_optimal_structure(
    nodes: List[PhysicsNode],
    max_nodes: int = 5
) -> Tuple[List[str], float]:
    """
    최고 구성 = argmax(Total Value)
    
    가장 가치 높은 노드 조합 찾기
    """
    # 가치 순 정렬
    sorted_nodes = sorted(nodes, key=lambda x: x.total_value_krw, reverse=True)
    
    # 상위 N개 선택
    optimal = sorted_nodes[:max_nodes]
    optimal_ids = [n.node_id for n in optimal]
    optimal_value = sum(n.total_value_krw for n in optimal)
    
    return optimal_ids, optimal_value


# ═══════════════════════════════════════════════════════════════════════════════════════════
# Physics Map 엔진 (통합)
# ═══════════════════════════════════════════════════════════════════════════════════════════

class PhysicsEngine:
    """Physics Map 계산 엔진"""
    
    def __init__(self, config: PhysicsConfig = None):
        self.config = config or DEFAULT_CONFIG
        self.nodes: Dict[str, PhysicsNode] = {}
        self.links: List[SynergyLink] = []
    
    def add_node(
        self,
        node_id: str,
        name: str,
        inflow: float = 0,
        outflow: float = 0,
        hours: float = 0,
        connections: int = 0
    ) -> PhysicsNode:
        """노드 추가"""
        node = PhysicsNode(
            node_id=node_id,
            name=name,
            money=MoneyFlow(inflow_krw=inflow, outflow_krw=outflow),
            time=TimeInvestment(hours=hours, hourly_value=self.config.hourly_value_krw),
            connection_count=connections
        )
        self.nodes[node_id] = node
        return node
    
    def add_link(
        self,
        node_a: str,
        node_b: str,
        distance: float = 1.0,
        strength: float = 0.5
    ) -> SynergyLink:
        """연결 추가"""
        link = SynergyLink(
            node_a=node_a,
            node_b=node_b,
            distance=distance,
            strength=strength
        )
        self.links.append(link)
        return link
    
    def compute_all_synergy(self) -> Dict[str, float]:
        """모든 노드의 시너지 계산"""
        synergy_by_node: Dict[str, float] = {nid: 0.0 for nid in self.nodes}
        
        for link in self.links:
            if link.node_a not in self.nodes or link.node_b not in self.nodes:
                continue
            
            node_a = self.nodes[link.node_a]
            node_b = self.nodes[link.node_b]
            
            # 중력 법칙 시너지
            synergy = compute_synergy_gravity(
                n1=max(1, node_a.connection_count),
                n2=max(1, node_b.connection_count),
                distance=link.distance,
                k=self.config.synergy_constant_k,
                r=self.config.compound_rate_r,
                t=3  # 3개월 기준
            )
            
            # 양쪽 노드에 배분
            synergy_by_node[link.node_a] += synergy / 2
            synergy_by_node[link.node_b] += synergy / 2
        
        return synergy_by_node
    
    def compute(self) -> PhysicsResult:
        """전체 계산 실행"""
        result = PhysicsResult(config=self.config)
        
        # 1. 시너지 계산
        synergy_map = self.compute_all_synergy()
        
        # 2. 각 노드 가치 계산
        for node_id, node in self.nodes.items():
            node.synergy_money_krw = synergy_map.get(node_id, 0)
            node.compute_value()
            
            # 상태 체크
            if node.total_value_krw < 0:
                node.status = NodeStatus.DANGER
            elif node.total_value_krw < self.config.delete_threshold_krw:
                node.status = NodeStatus.DELETE
            elif node.total_value_krw < self.config.delete_threshold_krw * 2:
                node.status = NodeStatus.WARNING
            else:
                node.status = NodeStatus.NORMAL
        
        result.nodes = self.nodes
        result.links = self.links
        
        # 3. 집계
        result.total_direct_money = sum(n.direct_money_krw for n in self.nodes.values())
        result.total_time_cost = sum(n.time_cost_krw for n in self.nodes.values())
        result.total_synergy_money = sum(n.synergy_money_krw for n in self.nodes.values())
        result.total_value = sum(n.total_value_krw for n in self.nodes.values())
        
        # 4. 삭제 대상
        result.delete_targets = get_delete_priority(
            list(self.nodes.values()),
            self.config.delete_threshold_krw
        )
        
        # 5. 최적 구성
        result.optimal_structure, result.optimal_value = find_optimal_structure(
            list(self.nodes.values()),
            max_nodes=5
        )
        
        # 6. 미래 예측
        result.growth_rate = compute_growth_rate(
            synergy_increase=min(0.15, result.total_synergy_money / max(1, result.total_value)),
            delete_savings=0.03 if result.delete_targets else 0,
            external_boost=0.10
        )
        result.future_value_12m = compute_future_value(
            result.total_value,
            result.growth_rate / 12,  # 월별 성장률
            self.config.forecast_months
        )
        
        return result
    
    def report(self) -> str:
        """결과 리포트"""
        result = self.compute()
        
        lines = [
            "=" * 70,
            "🌌 AUTUS Physics Map - Calculation Report",
            "=" * 70,
            "",
            "📊 전체 요약",
            "-" * 50,
            f"   직접 돈 합계:    ₩{result.total_direct_money:>15,.0f}",
            f"   시간 비용 합계:  ₩{result.total_time_cost:>15,.0f}",
            f"   시너지 돈 합계:  ₩{result.total_synergy_money:>15,.0f}",
            f"   ─────────────────────────────────────────",
            f"   총 가치:         ₩{result.total_value:>15,.0f}",
            "",
            "📈 미래 예측 (12개월)",
            "-" * 50,
            f"   월 성장률:       {result.growth_rate:.1%}",
            f"   12개월 후 가치:  ₩{result.future_value_12m:>15,.0f}",
            "",
            "🏆 최적 구성 (Top 5)",
            "-" * 50,
        ]
        
        for nid in result.optimal_structure:
            node = result.nodes[nid]
            lines.append(f"   {node.name}: ₩{node.total_value_krw:,.0f}")
        
        lines.extend([
            "",
            "🗑️ 삭제 대상",
            "-" * 50,
        ])
        
        if result.delete_targets:
            for nid in result.delete_targets[:5]:
                node = result.nodes[nid]
                lines.append(f"   {node.name}: ₩{node.total_value_krw:,.0f} ({node.status.value})")
        else:
            lines.append("   없음")
        
        lines.extend([
            "",
            "📋 노드별 상세",
            "-" * 50,
        ])
        
        for node in sorted(self.nodes.values(), key=lambda x: x.total_value_krw, reverse=True):
            lines.append(f"   [{node.status.value:8}] {node.name}")
            lines.append(f"              직접: ₩{node.direct_money_krw:,.0f}")
            lines.append(f"              시간: -₩{node.time_cost_krw:,.0f}")
            lines.append(f"              시너지: +₩{node.synergy_money_krw:,.0f}")
            lines.append(f"              = ₩{node.total_value_krw:,.0f}")
            lines.append("")
        
        lines.append("=" * 70)
        
        return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════════════════════════
# AUTUS PIPELINE 통합
# ═══════════════════════════════════════════════════════════════════════════════════════════

def from_pipeline_result(
    kpi: Dict[str, Any],
    roles: List[Dict[str, Any]],
    synergy: List[Dict[str, Any]],
    config: PhysicsConfig = None
) -> PhysicsEngine:
    """
    AUTUS PIPELINE 결과를 Physics Map으로 변환
    """
    engine = PhysicsEngine(config)
    
    # 노드 생성 (역할 기반)
    for role in roles:
        person_id = role.get("person_id", role.get("person", ""))
        role_name = role.get("role", "UNKNOWN")
        
        # KPI에서 개인 데이터 추출 (있으면)
        person_kpi = role.get("kpi", {})
        inflow = person_kpi.get("mint_krw", kpi.get("mint_krw", 0) / max(1, len(roles)))
        outflow = person_kpi.get("burn_krw", kpi.get("burn_krw", 0) / max(1, len(roles)))
        
        engine.add_node(
            node_id=person_id,
            name=f"{person_id} ({role_name})",
            inflow=inflow,
            outflow=outflow,
            hours=role.get("hours", 40),  # 기본 40시간
            connections=role.get("connections", 1)
        )
    
    # 시너지 연결 생성
    for syn in synergy:
        pair = syn.get("pair", "")
        if "_" in pair:
            a, b = pair.split("_", 1)
            uplift = syn.get("uplift", syn.get("pair_uplift", 0))
            
            # 시너지 강도 계산 (uplift 기반)
            strength = min(1.0, max(0.1, uplift / 100)) if uplift > 0 else 0.1
            
            engine.add_link(a, b, distance=1.0, strength=strength)
    
    return engine


# ═══════════════════════════════════════════════════════════════════════════════════════════
# Quick Test
# ═══════════════════════════════════════════════════════════════════════════════════════════

def demo():
    """데모 실행"""
    print("\n🌌 Physics Map Demo")
    print("=" * 70)
    
    # 엔진 생성
    engine = PhysicsEngine()
    
    # 노드 추가 (스포츠 아카데미 예시)
    engine.add_node("COACH1", "코치 김", inflow=80_000_000, outflow=10_000_000, hours=160, connections=100)
    engine.add_node("COACH2", "코치 박", inflow=50_000_000, outflow=8_000_000, hours=120, connections=50)
    engine.add_node("COACH3", "코치 이", inflow=20_000_000, outflow=15_000_000, hours=200, connections=20)
    engine.add_node("ADMIN", "관리자", inflow=5_000_000, outflow=3_000_000, hours=80, connections=10)
    engine.add_node("INTERN", "인턴", inflow=1_000_000, outflow=2_000_000, hours=160, connections=5)
    
    # 연결 추가
    engine.add_link("COACH1", "COACH2", distance=1.0, strength=0.8)
    engine.add_link("COACH1", "COACH3", distance=2.0, strength=0.5)
    engine.add_link("COACH2", "COACH3", distance=1.5, strength=0.6)
    engine.add_link("COACH1", "ADMIN", distance=1.0, strength=0.4)
    engine.add_link("ADMIN", "INTERN", distance=1.0, strength=0.3)
    
    # 리포트 출력
    print(engine.report())
    
    return engine.compute()


if __name__ == "__main__":
    demo()
