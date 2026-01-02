"""
AUTUS Physics Engine Core
=========================
SehoOS EP10 - Musk Metcalfe's Law (AUTUS Edition, Physics-only)

핵심 원칙:
- 연결 수(n²)가 아닌 "검증된 Coin-flow 링크"로 가치 정의
- 의미 해석 금지 - 모든 것은 물리량(돈, 시간)으로만 측정
- Event로 검증된 링크만 인정
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple
from datetime import datetime, timedelta
from enum import Enum
import math
import json
from collections import defaultdict


# ═══════════════════════════════════════════════════════════════════════════
# 1. 기본 타입 정의
# ═══════════════════════════════════════════════════════════════════════════

class DragType(Enum):
    """드래그 입력 타입 (의미 해석 금지 - 물리 입력만)"""
    ALLOCATION = "allocation"  # Minutes 배분 변경
    LINK = "link"              # 링크 강도 변경
    SWAP = "swap"              # 팀 구성 변경


class EventType(Enum):
    """이벤트 타입 (산업별 매핑)"""
    MINT = "mint"      # 돈 생성 (매출, 수입)
    BURN = "burn"      # 돈 소멸 (비용, 지출)
    TRANSFER = "transfer"  # 돈 이동


@dataclass
class Event:
    """
    검증된 이벤트 (AUTUS의 유일한 실재)
    - 확정 금액
    - 확정 시간
    - 증빙
    """
    event_id: str
    timestamp: datetime
    event_type: EventType
    amount: float  # KRW (coin)
    minutes: float  # 소요 시간
    
    # 파티션 키 (LOCK)
    industry_id: str
    customer_id: str
    project_id: str
    
    # 참여자
    participants: List[str]  # person_id 목록
    
    # 증빙
    evidence: Optional[str] = None
    
    @property
    def velocity(self) -> float:
        """이벤트 속도 (coin/minute)"""
        if self.minutes <= 0:
            return 0.0
        return self.amount / self.minutes


@dataclass
class Person:
    """
    사람 노드 상태 벡터
    - Money_i: 누적 coin
    - Minutes_i: 누적 시간
    - b_i: 단독 기준선 (BaseRate)
    """
    person_id: str
    name: str
    
    # 상태 벡터
    total_coin: float = 0.0
    total_minutes: float = 0.0
    solo_events: List[str] = field(default_factory=list)
    
    @property
    def base_rate(self) -> float:
        """단독 기준선 b_i (solo velocity)"""
        if self.total_minutes <= 0:
            return 0.0
        return self.total_coin / self.total_minutes


@dataclass
class Link:
    """
    검증된 링크 (i ↔ j)
    - 공동 이벤트로 검증된 coin-flow
    - Φ_ij: 링크 에너지
    """
    person_i: str
    person_j: str
    
    # 공동 이벤트 목록
    joint_events: List[str] = field(default_factory=list)
    
    # 링크 물리량
    phi: float = 0.0  # 링크 에너지 (양수만)
    total_uplift: float = 0.0  # 누적 uplift


@dataclass
class IndustryParams:
    """
    산업별 파라미터 (θ_bucket)
    - 물리법칙은 동일, 파라미터만 다름
    """
    industry_id: str
    name: str
    
    # 파라미터
    lambda_decay: float = 0.1      # 간접 감쇠
    gamma_bonus: float = 0.05      # 결합 보너스
    alpha_sensitivity: float = 0.2  # 업데이트 민감도
    
    # 이벤트 타입 매핑
    event_catalog: Dict[str, EventType] = field(default_factory=dict)


# ═══════════════════════════════════════════════════════════════════════════
# 2. Physics Scale Law (AUTUS Edition)
# ═══════════════════════════════════════════════════════════════════════════

class PhysicsEngine:
    """
    AUTUS Physics Engine
    
    Musk Metcalfe's Law:
    V(t) = Σ Φ_ij(t)  (검증된 링크 에너지 합)
    
    링크 에너지:
    Φ_ij = Σ max(0, u_ij,e) × Minutes_e
    u_ij,e = v_e - (b_i + b_j) / 2  (pair uplift)
    """
    
    def __init__(self):
        self.persons: Dict[str, Person] = {}
        self.events: Dict[str, Event] = {}
        self.links: Dict[Tuple[str, str], Link] = {}
        self.industry_params: Dict[str, IndustryParams] = {}
        
        # Audit log (append-only)
        self.audit_log: List[Dict] = []
        
        # 초기 산업 파라미터 설정
        self._init_industry_params()
    
    def _init_industry_params(self):
        """산업별 파라미터 초기값 (θ_bucket 3종)"""
        
        # 서비스업
        self.industry_params["service"] = IndustryParams(
            industry_id="service",
            name="서비스업",
            lambda_decay=0.08,
            gamma_bonus=0.06,
            alpha_sensitivity=0.25,
            event_catalog={
                "consultation": EventType.MINT,
                "project_fee": EventType.MINT,
                "operating_cost": EventType.BURN,
                "commission": EventType.TRANSFER
            }
        )
        
        # 교육
        self.industry_params["education"] = IndustryParams(
            industry_id="education",
            name="교육",
            lambda_decay=0.12,
            gamma_bonus=0.08,
            alpha_sensitivity=0.20,
            event_catalog={
                "tuition": EventType.MINT,
                "coaching_fee": EventType.MINT,
                "facility_cost": EventType.BURN,
                "referral_bonus": EventType.TRANSFER
            }
        )
        
        # 건설
        self.industry_params["construction"] = IndustryParams(
            industry_id="construction",
            name="건설",
            lambda_decay=0.15,
            gamma_bonus=0.04,
            alpha_sensitivity=0.15,
            event_catalog={
                "contract": EventType.MINT,
                "material_cost": EventType.BURN,
                "labor_cost": EventType.BURN,
                "subcontract": EventType.TRANSFER
            }
        )
    
    # ─────────────────────────────────────────────────────────────────────
    # 2.1 이벤트 처리
    # ─────────────────────────────────────────────────────────────────────
    
    def add_event(self, event: Event) -> None:
        """이벤트 추가 및 물리량 계산"""
        
        self.events[event.event_id] = event
        
        # 참여자 상태 업데이트
        per_person_amount = event.amount / len(event.participants)
        per_person_minutes = event.minutes / len(event.participants)
        
        for pid in event.participants:
            if pid not in self.persons:
                self.persons[pid] = Person(person_id=pid, name=pid)
            
            person = self.persons[pid]
            person.total_coin += per_person_amount
            person.total_minutes += per_person_minutes
            
            # 단독 이벤트 추적
            if len(event.participants) == 1:
                person.solo_events.append(event.event_id)
        
        # 링크 업데이트 (2명 이상 참여시)
        if len(event.participants) >= 2:
            self._update_links(event)
        
        # Audit log
        self._log_audit("event_added", {
            "event_id": event.event_id,
            "amount": event.amount,
            "participants": event.participants
        })
    
    def _update_links(self, event: Event) -> None:
        """링크 물리량 업데이트"""
        
        participants = event.participants
        
        # 모든 쌍에 대해 링크 업데이트
        for i in range(len(participants)):
            for j in range(i + 1, len(participants)):
                pid_i, pid_j = sorted([participants[i], participants[j]])
                link_key = (pid_i, pid_j)
                
                if link_key not in self.links:
                    self.links[link_key] = Link(person_i=pid_i, person_j=pid_j)
                
                link = self.links[link_key]
                link.joint_events.append(event.event_id)
                
                # Pair uplift 계산
                b_i = self.persons[pid_i].base_rate
                b_j = self.persons[pid_j].base_rate
                baseline = (b_i + b_j) / 2
                
                uplift = event.velocity - baseline
                
                # 양수 uplift만 인정
                if uplift > 0:
                    energy = uplift * event.minutes
                    link.phi += energy
                    link.total_uplift += uplift
    
    # ─────────────────────────────────────────────────────────────────────
    # 2.2 Scale Law 계산
    # ─────────────────────────────────────────────────────────────────────
    
    def calculate_network_value(self) -> float:
        """
        네트워크 가치 V(t) 계산
        V(t) = Σ Φ_ij(t)
        """
        return sum(link.phi for link in self.links.values())
    
    def calculate_verified_link_count(self) -> int:
        """검증된 링크 수 (Φ > 0인 링크만)"""
        return sum(1 for link in self.links.values() if link.phi > 0)
    
    def get_scale_metrics(self) -> Dict:
        """스케일 메트릭스"""
        n = len(self.persons)
        theoretical_n2 = n * (n - 1) / 2 if n > 1 else 0
        verified_links = self.calculate_verified_link_count()
        network_value = self.calculate_network_value()
        
        return {
            "node_count": n,
            "theoretical_links_n2": theoretical_n2,
            "verified_links": verified_links,
            "link_efficiency": verified_links / theoretical_n2 if theoretical_n2 > 0 else 0,
            "network_value_V": network_value,
            "avg_link_energy": network_value / verified_links if verified_links > 0 else 0
        }
    
    # ─────────────────────────────────────────────────────────────────────
    # 2.3 KPI 계산
    # ─────────────────────────────────────────────────────────────────────
    
    def calculate_kpi(self, days: int = 7) -> Dict:
        """
        KPI 계산 (Rolling)
        - NetCoin: Mint - Burn
        - EntropyRatio: Burn / Mint
        - Velocity: Total Coin / Total Minutes
        """
        cutoff = datetime.now() - timedelta(days=days)
        
        mint_total = 0.0
        burn_total = 0.0
        total_minutes = 0.0
        
        for event in self.events.values():
            if event.timestamp >= cutoff:
                if event.event_type == EventType.MINT:
                    mint_total += event.amount
                elif event.event_type == EventType.BURN:
                    burn_total += event.amount
                total_minutes += event.minutes
        
        net_coin = mint_total - burn_total
        entropy_ratio = burn_total / mint_total if mint_total > 0 else 0
        velocity = (mint_total + burn_total) / total_minutes if total_minutes > 0 else 0
        
        return {
            "period_days": days,
            "mint": mint_total,
            "burn": burn_total,
            "net_coin": net_coin,
            "entropy_ratio": entropy_ratio,
            "velocity": velocity
        }
    
    # ─────────────────────────────────────────────────────────────────────
    # 2.4 드래그 → 물리 입력 변환
    # ─────────────────────────────────────────────────────────────────────
    
    def apply_drag_input(
        self,
        drag_type: DragType,
        params: Dict
    ) -> Dict:
        """
        드래그 입력을 물리 입력으로 변환
        
        의미 해석 금지 - 3가지 물리 입력만:
        1. ALLOCATION: Minutes 배분 변경
        2. LINK: 링크 강도 변경
        3. SWAP: 팀 구성 변경
        """
        
        result = {
            "drag_type": drag_type.value,
            "input_params": params,
            "prediction_delta": {}
        }
        
        if drag_type == DragType.ALLOCATION:
            # Minutes 재배분
            person_id = params.get("person_id")
            delta_minutes = params.get("delta_minutes", 0)
            
            if person_id in self.persons:
                # 예측: Minutes 변화가 Velocity에 미치는 영향
                person = self.persons[person_id]
                new_minutes = person.total_minutes + delta_minutes
                
                if new_minutes > 0:
                    predicted_velocity_change = person.total_coin / new_minutes - person.base_rate
                    result["prediction_delta"]["velocity_change"] = predicted_velocity_change
        
        elif drag_type == DragType.LINK:
            # 링크 강도 변경 (시뮬레이션용)
            person_i = params.get("person_i")
            person_j = params.get("person_j")
            weight_delta = params.get("weight_delta", 0)
            
            link_key = tuple(sorted([person_i, person_j]))
            if link_key in self.links:
                link = self.links[link_key]
                # 예측: 링크 강화시 추가 uplift 기대값
                avg_uplift = link.total_uplift / len(link.joint_events) if link.joint_events else 0
                result["prediction_delta"]["expected_uplift"] = avg_uplift * (1 + weight_delta)
        
        elif drag_type == DragType.SWAP:
            # 팀 구성 변경
            team_out = params.get("person_out")
            team_in = params.get("person_in")
            
            # 예측: 팀 점수 변화
            current_team_score = self._calculate_team_score(params.get("team", []))
            new_team = [p for p in params.get("team", []) if p != team_out] + [team_in]
            new_team_score = self._calculate_team_score(new_team)
            
            result["prediction_delta"]["team_score_change"] = new_team_score - current_team_score
        
        # Audit log
        self._log_audit("drag_input", result)
        
        return result
    
    def _calculate_team_score(self, team: List[str]) -> float:
        """팀 점수 계산 (링크 에너지 합)"""
        score = 0.0
        for i in range(len(team)):
            for j in range(i + 1, len(team)):
                link_key = tuple(sorted([team[i], team[j]]))
                if link_key in self.links:
                    score += self.links[link_key].phi
        return score
    
    # ─────────────────────────────────────────────────────────────────────
    # 2.5 예측 엔진 (Rolling Horizon)
    # ─────────────────────────────────────────────────────────────────────
    
    def predict_kpi(
        self,
        horizon_days: int = 7,
        drag_inputs: Optional[List[Dict]] = None
    ) -> Dict:
        """
        Rolling Horizon 예측
        - 확률 분포/범위로 출력 (서사 금지)
        """
        
        # 현재 KPI
        current_kpi = self.calculate_kpi(days=7)
        
        # 기본 예측 (현재 추세 유지)
        base_mint_rate = current_kpi["mint"] / 7  # 일평균
        base_burn_rate = current_kpi["burn"] / 7
        
        predicted_mint = base_mint_rate * horizon_days
        predicted_burn = base_burn_rate * horizon_days
        
        # 드래그 입력 반영
        if drag_inputs:
            for drag in drag_inputs:
                drag_type = DragType(drag.get("type", "allocation"))
                delta = self.apply_drag_input(drag_type, drag.get("params", {}))
                
                # 예측 조정
                if "velocity_change" in delta.get("prediction_delta", {}):
                    velocity_factor = 1 + delta["prediction_delta"]["velocity_change"] * 0.1
                    predicted_mint *= velocity_factor
        
        # EntropyRatio 기반 Burn 예측
        entropy_ratio = current_kpi["entropy_ratio"]
        predicted_burn = predicted_mint * entropy_ratio
        
        predicted_net = predicted_mint - predicted_burn
        
        # Best Team Score
        best_team = self._find_best_team(team_size=3)
        
        return {
            "horizon_days": horizon_days,
            "predicted_mint": predicted_mint,
            "predicted_burn": predicted_burn,
            "predicted_net_coin": predicted_net,
            "predicted_entropy_ratio": entropy_ratio,
            "best_team": best_team["team"],
            "best_team_score": best_team["score"],
            "confidence": 0.7  # 기본 신뢰도
        }
    
    def _find_best_team(self, team_size: int = 3) -> Dict:
        """최적 팀 찾기"""
        if len(self.persons) < team_size:
            return {"team": list(self.persons.keys()), "score": 0}
        
        from itertools import combinations
        
        best_team = []
        best_score = -float('inf')
        
        for team in combinations(self.persons.keys(), team_size):
            score = self._calculate_team_score(list(team))
            if score > best_score:
                best_score = score
                best_team = list(team)
        
        return {"team": best_team, "score": best_score}
    
    # ─────────────────────────────────────────────────────────────────────
    # 2.6 자동 트리거
    # ─────────────────────────────────────────────────────────────────────
    
    def check_auto_triggers(self) -> List[Dict]:
        """자동 교체 트리거 확인"""
        triggers = []
        kpi = self.calculate_kpi(days=7)
        
        # EntropyRatio 상승 시
        if kpi["entropy_ratio"] > 0.7:
            triggers.append({
                "type": "REBALANCE",
                "reason": f"EntropyRatio {kpi['entropy_ratio']:.2f} > 0.7",
                "urgency": "high"
            })
        elif kpi["entropy_ratio"] > 0.5:
            triggers.append({
                "type": "SHRINK",
                "reason": f"EntropyRatio {kpi['entropy_ratio']:.2f} > 0.5",
                "urgency": "medium"
            })
        
        # Velocity 개선 시
        if kpi["velocity"] > 10000:  # coin/minute 기준
            triggers.append({
                "type": "EXPAND",
                "reason": f"Velocity {kpi['velocity']:.0f} > 10,000",
                "urgency": "low"
            })
        
        return triggers
    
    # ─────────────────────────────────────────────────────────────────────
    # 2.7 Audit
    # ─────────────────────────────────────────────────────────────────────
    
    def _log_audit(self, action: str, data: Dict) -> None:
        """Audit 로그 (append-only)"""
        self.audit_log.append({
            "timestamp": datetime.now().isoformat(),
            "action": action,
            "data": data
        })
    
    def export_audit_log(self) -> str:
        """Audit 로그 JSONL 내보내기"""
        return "\n".join(json.dumps(entry, ensure_ascii=False) for entry in self.audit_log)
    
    # ─────────────────────────────────────────────────────────────────────
    # 2.8 상태 내보내기 (UI용)
    # ─────────────────────────────────────────────────────────────────────
    
    def get_map_state(self) -> Dict:
        """
        Physics Map UI용 상태
        - 사람: 점(노드)
        - 돈: 노드 옆 숫자
        - 링크: 기본 숨김 (요청시만)
        """
        
        nodes = []
        for person in self.persons.values():
            nodes.append({
                "id": person.person_id,
                "name": person.name,
                "coin": person.total_coin,
                "coin_rate": person.base_rate,
                # 좌표는 UI에서 결정 (물리 엔진은 좌표 무관심)
            })
        
        # 링크는 기본 숨김, 요청시만
        links = []
        for link in self.links.values():
            if link.phi > 0:
                links.append({
                    "source": link.person_i,
                    "target": link.person_j,
                    "phi": link.phi,
                    "event_count": len(link.joint_events)
                })
        
        kpi = self.calculate_kpi(days=7)
        prediction = self.predict_kpi(horizon_days=7)
        triggers = self.check_auto_triggers()
        
        return {
            "nodes": nodes,
            "links": links,
            "kpi_current": kpi,
            "kpi_predicted": prediction,
            "triggers": triggers,
            "scale_metrics": self.get_scale_metrics()
        }


# ═══════════════════════════════════════════════════════════════════════════
# 3. 테스트 / 데모
# ═══════════════════════════════════════════════════════════════════════════

def demo():
    """데모 시나리오 (교육 산업)"""
    
    engine = PhysicsEngine()
    
    # 사람 추가
    persons = ["오세호", "김경희", "오선우", "오연우", "오은우"]
    for name in persons:
        engine.persons[name] = Person(person_id=name, name=name)
    
    # 이벤트 추가
    events = [
        # 단독 이벤트 (기준선 설정)
        Event(
            event_id="E001",
            timestamp=datetime.now() - timedelta(days=5),
            event_type=EventType.MINT,
            amount=5000000,
            minutes=480,  # 8시간
            industry_id="education",
            customer_id="C001",
            project_id="P001",
            participants=["오세호"]
        ),
        Event(
            event_id="E002",
            timestamp=datetime.now() - timedelta(days=4),
            event_type=EventType.MINT,
            amount=2000000,
            minutes=360,
            industry_id="education",
            customer_id="C001",
            project_id="P001",
            participants=["김경희"]
        ),
        # 공동 이벤트 (링크 형성)
        Event(
            event_id="E003",
            timestamp=datetime.now() - timedelta(days=3),
            event_type=EventType.MINT,
            amount=8000000,
            minutes=600,
            industry_id="education",
            customer_id="C002",
            project_id="P002",
            participants=["오세호", "오선우"]
        ),
        Event(
            event_id="E004",
            timestamp=datetime.now() - timedelta(days=2),
            event_type=EventType.MINT,
            amount=6000000,
            minutes=480,
            industry_id="education",
            customer_id="C003",
            project_id="P003",
            participants=["오세호", "김경희", "오선우"]
        ),
        Event(
            event_id="E005",
            timestamp=datetime.now() - timedelta(days=1),
            event_type=EventType.BURN,
            amount=3000000,
            minutes=240,
            industry_id="education",
            customer_id="C001",
            project_id="P001",
            participants=["오연우", "오은우"]
        ),
    ]
    
    for event in events:
        engine.add_event(event)
    
    # 결과 출력
    print("=" * 60)
    print("AUTUS Physics Engine - Demo Results")
    print("=" * 60)
    
    state = engine.get_map_state()
    
    print("\n📊 Scale Metrics (Musk Metcalfe's Law):")
    metrics = state["scale_metrics"]
    print(f"  Node Count: {metrics['node_count']}")
    print(f"  Theoretical Links (n²): {metrics['theoretical_links_n2']}")
    print(f"  Verified Links: {metrics['verified_links']}")
    print(f"  Link Efficiency: {metrics['link_efficiency']:.1%}")
    print(f"  Network Value V(t): ₩{metrics['network_value_V']:,.0f}")
    
    print("\n💰 Current KPI (7D):")
    kpi = state["kpi_current"]
    print(f"  Mint: ₩{kpi['mint']:,.0f}")
    print(f"  Burn: ₩{kpi['burn']:,.0f}")
    print(f"  NetCoin: ₩{kpi['net_coin']:,.0f}")
    print(f"  EntropyRatio: {kpi['entropy_ratio']:.2f}")
    print(f"  Velocity: ₩{kpi['velocity']:,.0f}/min")
    
    print("\n🔮 Prediction (7D):")
    pred = state["kpi_predicted"]
    print(f"  Predicted NetCoin: ₩{pred['predicted_net_coin']:,.0f}")
    print(f"  Best Team: {pred['best_team']}")
    print(f"  Best Team Score: ₩{pred['best_team_score']:,.0f}")
    
    print("\n⚡ Auto Triggers:")
    for trigger in state["triggers"]:
        print(f"  [{trigger['urgency'].upper()}] {trigger['type']}: {trigger['reason']}")
    
    print("\n👥 Nodes (사람 + 돈):")
    for node in state["nodes"]:
        print(f"  {node['name']}: ₩{node['coin']:,.0f} (Rate: ₩{node['coin_rate']:,.0f}/min)")
    
    print("\n🔗 Verified Links (Φ > 0):")
    for link in state["links"]:
        print(f"  {link['source']} ↔ {link['target']}: Φ=₩{link['phi']:,.0f} ({link['event_count']} events)")
    
    return engine


if __name__ == "__main__":
    demo()
