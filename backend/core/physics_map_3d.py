"""
AUTUS 3D Physics Map Engine (Bezos Edition)
============================================

3차원 물리 지도: 사람을 입자로, 관계를 중력으로

좌표계:
- x축 (돈): 순수익 기여도 → 오른쪽이 좋음
- y축 (시간): 소모 시간 → 아래쪽이 좋음 (효율적)
- z축 (시너지): 결합 에너지 → 앞쪽이 좋음

골든 볼륨: 오른쪽 + 아래쪽 + 앞쪽 = 최고 가치

클러스터:
1. Golden (골든): 최고 가치 핵
2. Efficiency (효율): 고효율 지대
3. High Energy (고에너지): 불안정 거성
4. Stable (안정): 기초 질량
5. Removal (제거): 엔트로피 생성원

Version: 2.0.0
Status: LOCKED
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, Set, Any
from datetime import datetime, timedelta
from enum import Enum
import math
import json
import random


# ================================================================
# CONSTANTS
# ================================================================

# 시너지 계산 가중치
SYNERGY_WEIGHTS = {
    "fitness": 0.35,      # 역할 적합도
    "density": 0.25,      # 상호작용 밀도
    "frequency": 0.20,    # 접촉 빈도
    "penalty": 0.20,      # 갈등/마찰 패널티
}

# 클러스터 임계값
CLUSTER_THRESHOLDS = {
    "golden_x": 0.7,      # x축 상위 30%
    "golden_z": 0.7,      # z축 상위
    "efficiency_x": 0.4,  # x축 중상
    "efficiency_y": 0.3,  # y축 하위 (효율적)
    "high_energy_x": 0.6, # x축 상위
    "high_energy_z": 0.0, # z축 중립 이하
    "removal_x": 0.2,     # x축 하위
    "removal_z": -0.5,    # z축 음수
}

# 정규화 범위
NORM_RANGE = {
    "x_min": -1000000,    # 최소 순수익 (음수 가능)
    "x_max": 10000000,    # 최대 순수익
    "y_min": 0,           # 최소 시간
    "y_max": 200,         # 최대 시간 (시간/월)
}


# ================================================================
# ENUMS
# ================================================================

class ClusterType(str, Enum):
    GOLDEN = "GOLDEN"           # 골든 볼륨 (최고 가치)
    EFFICIENCY = "EFFICIENCY"   # 고효율 지대
    HIGH_ENERGY = "HIGH_ENERGY" # 불안정 거성
    STABLE = "STABLE"           # 안정 구역
    REMOVAL = "REMOVAL"         # 제거 대상


class ActionType(str, Enum):
    AMPLIFY = "AMPLIFY"               # 중력 증폭
    EXPAND_ROLE = "EXPAND_ROLE"       # 역할 확장
    STRENGTHEN = "STRENGTHEN"         # 결속 강화
    STABILIZE = "STABILIZE"           # 궤도 안정
    ACCELERATE = "ACCELERATE"         # 효율 가속
    BOOST_SYNERGY = "BOOST_SYNERGY"   # 시너지 향상
    REASSIGN = "REASSIGN"             # 역할 재배치
    MAINTAIN = "MAINTAIN"             # 현 상태 유지
    DECAY = "DECAY"                   # 점진적 분리
    EJECT = "EJECT"                   # 궤도 이탈


# ================================================================
# DATA STRUCTURES
# ================================================================

@dataclass
class Node3D:
    """3D 공간의 노드"""
    id: str
    name: str
    
    # 원시 데이터
    revenue: float          # 순수익 (원)
    time_spent: float       # 소모 시간 (시간/월)
    fitness: float          # 역할 적합도 (0-1)
    density: float          # 상호작용 밀도 (0-1)
    frequency: float        # 접촉 빈도 (0-1)
    penalty: float          # 갈등/마찰 패널티 (0-1)
    
    # 정규화된 3D 좌표
    x: float = 0.0          # 돈 축 (-1 ~ 1)
    y: float = 0.0          # 시간 축 (0 ~ 1, 낮을수록 좋음)
    z: float = 0.0          # 시너지 축 (-1 ~ 1)
    
    # 클러스터 정보
    cluster: Optional[ClusterType] = None
    
    # 메타데이터
    tags: List[str] = field(default_factory=list)
    connections: List[str] = field(default_factory=list)


@dataclass
class Cluster:
    """클러스터 정보"""
    cluster_type: ClusterType
    nodes: List[Node3D]
    centroid: Tuple[float, float, float]  # (x, y, z)
    
    # 통계
    avg_revenue: float
    avg_time: float
    avg_synergy: float
    total_value: float
    
    # 권장 액션
    recommended_action: ActionType
    action_description: str


@dataclass
class GoldenVolume:
    """골든 볼륨 정보"""
    nodes: List[Node3D]
    total_value: float
    avg_synergy: float
    
    # 경계
    x_threshold: float
    y_threshold: float
    z_threshold: float


@dataclass
class PhysicsMapReport:
    """3D Physics Map 리포트"""
    timestamp: datetime
    total_nodes: int
    
    # 클러스터별 현황
    clusters: Dict[ClusterType, Cluster]
    
    # 골든 볼륨
    golden_volume: GoldenVolume
    
    # 엔트로피
    system_entropy: float
    money_efficiency: float
    
    # 가치 폭발 시뮬레이션
    current_value: float
    projected_value: float
    value_multiplier: float
    
    # 액션 리스트
    amplify_targets: List[Node3D]
    removal_targets: List[Node3D]


# ================================================================
# SYNERGY CALCULATOR
# ================================================================

class SynergyCalculator:
    """
    시너지 강도 계산기
    
    z = tanh(w1×fitness + w2×density + w3×frequency - w4×penalty)
    
    tanh 함수 특성:
    - 출력 범위: -1 ~ +1
    - 0 근처에서 민감 (초기 가속도)
    - 극단값 포화 (안정성)
    """
    
    def __init__(self, weights: Dict[str, float] = None):
        self.weights = weights or SYNERGY_WEIGHTS
    
    def calculate(
        self,
        fitness: float,
        density: float,
        frequency: float,
        penalty: float
    ) -> float:
        """
        시너지 강도 계산
        
        Returns:
            z: 시너지 강도 (-1 ~ +1)
        """
        # 가중 합계
        raw_score = (
            self.weights["fitness"] * fitness * 2 +
            self.weights["density"] * density * 2 +
            self.weights["frequency"] * frequency * 2 -
            self.weights["penalty"] * penalty * 3
        )
        
        # tanh 정규화
        z = math.tanh(raw_score)
        
        return z
    
    def calculate_pairwise(
        self,
        node1: Node3D,
        node2: Node3D
    ) -> float:
        """
        두 노드 간 페어 시너지 계산
        """
        # 상호 적합도 (기하평균)
        mutual_fitness = math.sqrt(node1.fitness * node2.fitness)
        
        # 상호작용 밀도 (산술평균)
        mutual_density = (node1.density + node2.density) / 2
        
        # 접촉 빈도 (최대값)
        mutual_frequency = max(node1.frequency, node2.frequency)
        
        # 패널티 (합산)
        mutual_penalty = (node1.penalty + node2.penalty) / 2
        
        return self.calculate(
            mutual_fitness,
            mutual_density,
            mutual_frequency,
            mutual_penalty
        )
    
    def get_synergy_grade(self, z: float) -> str:
        """시너지 등급"""
        if z >= 0.8:
            return "S (화이트홀)"
        elif z >= 0.6:
            return "A (핵심 연합)"
        elif z >= 0.3:
            return "B (시너지)"
        elif z >= 0:
            return "C (중립)"
        elif z >= -0.3:
            return "D (마찰)"
        elif z >= -0.6:
            return "E (갈등)"
        else:
            return "F (블랙홀)"


# ================================================================
# COORDINATE NORMALIZER
# ================================================================

class CoordinateNormalizer:
    """좌표 정규화"""
    
    def __init__(
        self,
        x_range: Tuple[float, float] = (NORM_RANGE["x_min"], NORM_RANGE["x_max"]),
        y_range: Tuple[float, float] = (NORM_RANGE["y_min"], NORM_RANGE["y_max"])
    ):
        self.x_min, self.x_max = x_range
        self.y_min, self.y_max = y_range
    
    def normalize_x(self, revenue: float) -> float:
        """
        x축 정규화 (돈)
        
        0 = 기준점, 양수 = 수익, 음수 = 손실
        """
        if revenue >= 0:
            # 0 ~ 1 범위로 정규화
            return min(1.0, revenue / self.x_max)
        else:
            # -1 ~ 0 범위로 정규화
            return max(-1.0, revenue / abs(self.x_min))
    
    def normalize_y(self, time_spent: float) -> float:
        """
        y축 정규화 (시간)
        
        0 = 최소 시간 (효율적), 1 = 최대 시간 (비효율)
        """
        if time_spent <= 0:
            return 0.0
        
        normalized = (time_spent - self.y_min) / (self.y_max - self.y_min)
        return min(1.0, max(0.0, normalized))
    
    def normalize_node(self, node: Node3D, synergy_calc: SynergyCalculator) -> Node3D:
        """노드 좌표 정규화"""
        node.x = self.normalize_x(node.revenue)
        node.y = self.normalize_y(node.time_spent)
        node.z = synergy_calc.calculate(
            node.fitness,
            node.density,
            node.frequency,
            node.penalty
        )
        
        return node


# ================================================================
# CLUSTER ENGINE
# ================================================================

class ClusterEngine:
    """
    클러스터링 엔진
    
    5개 클러스터:
    1. Golden: x↑, y↓, z↑ (최고 가치)
    2. Efficiency: x↑, y↓, z 중간 (고효율)
    3. High Energy: x↑, y↑, z↓ (불안정)
    4. Stable: x 중간, y 중간, z 중간 (안정)
    5. Removal: x↓, y↑, z↓ (제거 대상)
    """
    
    def __init__(self, thresholds: Dict = None):
        self.thresholds = thresholds or CLUSTER_THRESHOLDS
    
    def classify_node(self, node: Node3D) -> ClusterType:
        """노드 클러스터 분류"""
        x, y, z = node.x, node.y, node.z
        
        # 1. Removal (엔트로피 생성원)
        if x < self.thresholds["removal_x"] or z < self.thresholds["removal_z"]:
            return ClusterType.REMOVAL
        
        # 2. Golden (최고 가치)
        if x >= self.thresholds["golden_x"] and z >= self.thresholds["golden_z"]:
            return ClusterType.GOLDEN
        
        # 3. Efficiency (고효율)
        if x >= self.thresholds["efficiency_x"] and y <= self.thresholds["efficiency_y"]:
            return ClusterType.EFFICIENCY
        
        # 4. High Energy (불안정 거성)
        if x >= self.thresholds["high_energy_x"] and z < self.thresholds["high_energy_z"]:
            return ClusterType.HIGH_ENERGY
        
        # 5. Stable (안정)
        return ClusterType.STABLE
    
    def cluster_nodes(self, nodes: List[Node3D]) -> Dict[ClusterType, Cluster]:
        """전체 노드 클러스터링"""
        # 클러스터별 노드 분류
        cluster_nodes: Dict[ClusterType, List[Node3D]] = {
            ct: [] for ct in ClusterType
        }
        
        for node in nodes:
            cluster_type = self.classify_node(node)
            node.cluster = cluster_type
            cluster_nodes[cluster_type].append(node)
        
        # 클러스터 객체 생성
        clusters = {}
        
        for ct, node_list in cluster_nodes.items():
            if not node_list:
                continue
            
            # 중심점 계산
            centroid = (
                sum(n.x for n in node_list) / len(node_list),
                sum(n.y for n in node_list) / len(node_list),
                sum(n.z for n in node_list) / len(node_list),
            )
            
            # 통계
            avg_revenue = sum(n.revenue for n in node_list) / len(node_list)
            avg_time = sum(n.time_spent for n in node_list) / len(node_list)
            avg_synergy = sum(n.z for n in node_list) / len(node_list)
            total_value = sum(n.revenue for n in node_list)
            
            # 권장 액션
            action, desc = self._get_cluster_action(ct)
            
            clusters[ct] = Cluster(
                cluster_type=ct,
                nodes=node_list,
                centroid=centroid,
                avg_revenue=avg_revenue,
                avg_time=avg_time,
                avg_synergy=avg_synergy,
                total_value=total_value,
                recommended_action=action,
                action_description=desc,
            )
        
        return clusters
    
    def _get_cluster_action(self, ct: ClusterType) -> Tuple[ActionType, str]:
        """클러스터별 권장 액션"""
        actions = {
            ClusterType.GOLDEN: (
                ActionType.AMPLIFY,
                "n^n 폭발의 핵, 자원 집중 투입 및 복제"
            ),
            ClusterType.EFFICIENCY: (
                ActionType.BOOST_SYNERGY,
                "시너지 보정(z축 이동)으로 골든 진입 유도"
            ),
            ClusterType.HIGH_ENERGY: (
                ActionType.REASSIGN,
                "역할 재배치 필수, 시너지 회복 작업"
            ),
            ClusterType.STABLE: (
                ActionType.MAINTAIN,
                "시스템 기초 질량 지탱, 현 궤도 유지"
            ),
            ClusterType.REMOVAL: (
                ActionType.EJECT,
                "엔트로피 생성원, 즉시 차단 및 궤도 이탈"
            ),
        }
        
        return actions.get(ct, (ActionType.MAINTAIN, "상태 모니터링"))


# ================================================================
# GOLDEN VOLUME DETECTOR
# ================================================================

class GoldenVolumeDetector:
    """
    골든 볼륨 탐지기
    
    이상적 위치: 오른쪽(x↑), 아래(y↓), 앞쪽(z↑)
    """
    
    def __init__(
        self,
        x_threshold: float = 0.6,
        y_threshold: float = 0.4,
        z_threshold: float = 0.6
    ):
        self.x_threshold = x_threshold
        self.y_threshold = y_threshold
        self.z_threshold = z_threshold
    
    def detect(self, nodes: List[Node3D]) -> GoldenVolume:
        """골든 볼륨 탐지"""
        golden_nodes = []
        
        for node in nodes:
            # 오른쪽 + 아래쪽 + 앞쪽
            if (node.x >= self.x_threshold and
                node.y <= self.y_threshold and
                node.z >= self.z_threshold):
                golden_nodes.append(node)
        
        # 가치 순 정렬
        golden_nodes.sort(key=lambda n: n.revenue * (1 + n.z), reverse=True)
        
        total_value = sum(n.revenue for n in golden_nodes)
        avg_synergy = sum(n.z for n in golden_nodes) / len(golden_nodes) if golden_nodes else 0
        
        return GoldenVolume(
            nodes=golden_nodes,
            total_value=total_value,
            avg_synergy=avg_synergy,
            x_threshold=self.x_threshold,
            y_threshold=self.y_threshold,
            z_threshold=self.z_threshold,
        )
    
    def get_top_nodes(
        self,
        nodes: List[Node3D],
        top_k: int = 5
    ) -> List[Tuple[Node3D, ActionType, str]]:
        """상위 골든 노드 추출"""
        golden = self.detect(nodes)
        
        results = []
        for i, node in enumerate(golden.nodes[:top_k]):
            if i == 0:
                action = ActionType.AMPLIFY
                desc = "시스템 표준 모델로 복제"
            elif i < 3:
                action = ActionType.EXPAND_ROLE
                desc = "새로운 클러스터의 리더로 전진 배치"
            else:
                action = ActionType.STRENGTHEN
                desc = "핵심 인센티브 분사 및 결속력 강화"
            
            results.append((node, action, desc))
        
        return results


# ================================================================
# VALUE EXPLOSION CALCULATOR
# ================================================================

class ValueExplosionCalculator:
    """
    n^n 가치 폭발 계산기
    """
    
    def calculate_current_value(self, nodes: List[Node3D]) -> float:
        """현재 가치 계산"""
        n = len(nodes)
        if n == 0:
            return 0
        
        # 기본 가치: n²
        base_value = n ** 2
        
        # 시너지 보정
        avg_synergy = sum(n.z for n in nodes) / len(nodes)
        synergy_multiplier = 1 + (avg_synergy + 1) / 2  # 0.5 ~ 1.5
        
        return base_value * synergy_multiplier
    
    def calculate_projected_value(
        self,
        nodes: List[Node3D],
        removal_count: int = 0,
        optimization_factor: float = 1.0
    ) -> float:
        """
        최적화 후 예상 가치
        
        엔트로피 제거 + 골든 증폭 시
        """
        # 유효 노드 수 (제거 후)
        effective_n = len(nodes) - removal_count
        
        if effective_n <= 0:
            return 0
        
        # 최적화된 시너지 (엔트로피 제거로 상승)
        # 음수 시너지 노드 제거 효과
        positive_nodes = [n for n in nodes if n.z >= 0]
        if positive_nodes:
            avg_synergy = sum(n.z for n in positive_nodes) / len(positive_nodes)
        else:
            avg_synergy = 0
        
        # n^k 가치 (k = 2 + optimization_factor)
        k = 2 + optimization_factor
        base_value = effective_n ** k
        
        # 시너지 보정
        synergy_multiplier = 1 + (avg_synergy + 1) / 2 * 1.5
        
        return base_value * synergy_multiplier
    
    def calculate_entropy_impact(
        self,
        nodes: List[Node3D]
    ) -> Tuple[float, float]:
        """
        엔트로피 영향 계산
        
        Returns:
            (system_entropy, money_efficiency)
        """
        if not nodes:
            return 0, 1.0
        
        # 음수 시너지 비율
        negative_ratio = sum(1 for n in nodes if n.z < 0) / len(nodes)
        
        # 시스템 엔트로피
        system_entropy = negative_ratio * 10 + sum(n.penalty for n in nodes) / len(nodes) * 5
        
        # 돈 생산 효율
        money_efficiency = math.exp(-system_entropy / 5)
        
        return system_entropy, money_efficiency


# ================================================================
# 3D PHYSICS MAP ENGINE
# ================================================================

class PhysicsMap3DEngine:
    """
    3D Physics Map 메인 엔진
    """
    
    def __init__(self):
        self.synergy_calc = SynergyCalculator()
        self.normalizer = CoordinateNormalizer()
        self.cluster_engine = ClusterEngine()
        self.golden_detector = GoldenVolumeDetector()
        self.value_calc = ValueExplosionCalculator()
        
        self.nodes: List[Node3D] = []
        self.history: List[PhysicsMapReport] = []
    
    def add_node(
        self,
        id: str,
        name: str,
        revenue: float,
        time_spent: float,
        fitness: float = 0.5,
        density: float = 0.5,
        frequency: float = 0.5,
        penalty: float = 0.0,
        tags: List[str] = None
    ) -> Node3D:
        """노드 추가"""
        node = Node3D(
            id=id,
            name=name,
            revenue=revenue,
            time_spent=time_spent,
            fitness=fitness,
            density=density,
            frequency=frequency,
            penalty=penalty,
            tags=tags or [],
        )
        
        # 좌표 정규화
        node = self.normalizer.normalize_node(node, self.synergy_calc)
        
        self.nodes.append(node)
        
        return node
    
    def add_nodes_batch(self, nodes_data: List[Dict]) -> List[Node3D]:
        """노드 일괄 추가"""
        result = []
        for data in nodes_data:
            node = self.add_node(**data)
            result.append(node)
        return result
    
    def generate_report(self) -> PhysicsMapReport:
        """3D Physics Map 리포트 생성"""
        # 클러스터링
        clusters = self.cluster_engine.cluster_nodes(self.nodes)
        
        # 골든 볼륨
        golden_volume = self.golden_detector.detect(self.nodes)
        
        # 가치 계산
        removal_count = len(clusters.get(ClusterType.REMOVAL, Cluster(
            ClusterType.REMOVAL, [], (0,0,0), 0, 0, 0, 0, ActionType.EJECT, ""
        )).nodes) if ClusterType.REMOVAL in clusters else 0
        
        current_value = self.value_calc.calculate_current_value(self.nodes)
        projected_value = self.value_calc.calculate_projected_value(
            self.nodes,
            removal_count=removal_count,
            optimization_factor=0.5
        )
        
        # 엔트로피
        entropy, efficiency = self.value_calc.calculate_entropy_impact(self.nodes)
        
        # 증폭/제거 타겟
        amplify_targets = golden_volume.nodes[:5]
        removal_targets = clusters[ClusterType.REMOVAL].nodes if ClusterType.REMOVAL in clusters else []
        
        report = PhysicsMapReport(
            timestamp=datetime.now(),
            total_nodes=len(self.nodes),
            clusters=clusters,
            golden_volume=golden_volume,
            system_entropy=entropy,
            money_efficiency=efficiency,
            current_value=current_value,
            projected_value=projected_value,
            value_multiplier=projected_value / current_value if current_value > 0 else 0,
            amplify_targets=amplify_targets,
            removal_targets=removal_targets,
        )
        
        self.history.append(report)
        
        return report
    
    def get_node_actions(self, node: Node3D) -> Dict:
        """노드별 권장 액션"""
        cluster = node.cluster or self.cluster_engine.classify_node(node)
        
        actions = {
            ClusterType.GOLDEN: {
                "primary": "무한 증폭",
                "message": "당신의 가치는 현재 시스템 표준입니다",
                "incentive": "수익 배분율 15% 상향",
            },
            ClusterType.EFFICIENCY: {
                "primary": "시너지 향상",
                "message": "골든 볼륨 진입 임박",
                "incentive": "멘토링 프로그램 참여",
            },
            ClusterType.HIGH_ENERGY: {
                "primary": "역할 재배치",
                "message": "잠재력을 최대한 발휘할 새로운 역할 제안",
                "incentive": "전환 보너스",
            },
            ClusterType.STABLE: {
                "primary": "궤도 유지",
                "message": "시스템의 든든한 기반",
                "incentive": "안정 보너스",
            },
            ClusterType.REMOVAL: {
                "primary": "궤도 이탈",
                "message": "점진적 분리 프로세스",
                "incentive": None,
            },
        }
        
        return actions.get(cluster, actions[ClusterType.STABLE])
    
    def simulate_optimization(
        self,
        amplify_ids: List[str] = None,
        remove_ids: List[str] = None
    ) -> Dict:
        """최적화 시뮬레이션"""
        # 현재 상태
        current_entropy, current_efficiency = self.value_calc.calculate_entropy_impact(self.nodes)
        current_value = self.value_calc.calculate_current_value(self.nodes)
        
        # 시뮬레이션 노드
        sim_nodes = [n for n in self.nodes if n.id not in (remove_ids or [])]
        
        # 증폭 노드 시너지 향상
        for node in sim_nodes:
            if amplify_ids and node.id in amplify_ids:
                node.z = min(0.99, node.z + 0.2)
        
        # 최적화 후 상태
        new_entropy, new_efficiency = self.value_calc.calculate_entropy_impact(sim_nodes)
        new_value = self.value_calc.calculate_projected_value(
            sim_nodes,
            optimization_factor=0.5
        )
        
        return {
            "before": {
                "nodes": len(self.nodes),
                "entropy": current_entropy,
                "efficiency": current_efficiency,
                "value": current_value,
            },
            "after": {
                "nodes": len(sim_nodes),
                "entropy": new_entropy,
                "efficiency": new_efficiency,
                "value": new_value,
            },
            "improvement": {
                "entropy_reduction": current_entropy - new_entropy,
                "efficiency_gain": new_efficiency - current_efficiency,
                "value_multiplier": new_value / current_value if current_value > 0 else 0,
            },
        }
    
    def visualize_ascii(self) -> str:
        """ASCII 3D 시각화"""
        # 2D 투영 (x-z 평면, y는 기호로)
        grid_size = 20
        grid = [[" " for _ in range(grid_size + 1)] for _ in range(grid_size + 1)]
        
        # 축 그리기
        for i in range(grid_size + 1):
            grid[grid_size][i] = "─"
            grid[i][0] = "│"
        grid[grid_size][0] = "└"
        
        # 노드 배치
        cluster_symbols = {
            ClusterType.GOLDEN: "★",
            ClusterType.EFFICIENCY: "◆",
            ClusterType.HIGH_ENERGY: "▲",
            ClusterType.STABLE: "●",
            ClusterType.REMOVAL: "×",
        }
        
        for node in self.nodes:
            # x → 가로, z → 세로 (반전)
            col = int((node.x + 1) / 2 * (grid_size - 1)) + 1
            row = int((1 - (node.z + 1) / 2) * (grid_size - 1))
            
            col = max(1, min(grid_size - 1, col))
            row = max(0, min(grid_size - 1, row))
            
            symbol = cluster_symbols.get(node.cluster, "○")
            grid[row][col] = symbol
        
        # 문자열로 변환
        lines = ["".join(row) for row in grid]
        lines.append(" " + "─" * grid_size)
        lines.append("  └─ x(돈) →")
        lines.insert(0, "z(시너지)")
        lines.insert(1, "  ↑")
        
        return "\n".join(lines)


# ================================================================
# TEST
# ================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("AUTUS 3D Physics Map Engine Test")
    print("=" * 70)
    
    engine = PhysicsMap3DEngine()
    
    # 150명 노드 생성
    print("\n[1. 150명 노드 생성]")
    
    # 골든 노드 (상위 10%)
    for i in range(15):
        engine.add_node(
            id=f"golden_{i:02d}",
            name=f"Golden_{i}",
            revenue=random.randint(20000000, 50000000),
            time_spent=random.randint(20, 50),
            fitness=random.uniform(0.8, 1.0),
            density=random.uniform(0.7, 1.0),
            frequency=random.uniform(0.7, 1.0),
            penalty=random.uniform(0, 0.1),
            tags=["core", "leader"],
        )
    
    # 효율 노드 (20%)
    for i in range(30):
        engine.add_node(
            id=f"efficiency_{i:02d}",
            name=f"Efficiency_{i}",
            revenue=random.randint(5000000, 20000000),
            time_spent=random.randint(20, 40),
            fitness=random.uniform(0.5, 0.8),
            density=random.uniform(0.4, 0.7),
            frequency=random.uniform(0.5, 0.8),
            penalty=random.uniform(0, 0.2),
        )
    
    # 고에너지 노드 (15%)
    for i in range(22):
        engine.add_node(
            id=f"high_energy_{i:02d}",
            name=f"HighEnergy_{i}",
            revenue=random.randint(10000000, 30000000),
            time_spent=random.randint(100, 180),
            fitness=random.uniform(0.3, 0.6),
            density=random.uniform(0.2, 0.5),
            frequency=random.uniform(0.3, 0.6),
            penalty=random.uniform(0.3, 0.6),
        )
    
    # 안정 노드 (40%)
    for i in range(60):
        engine.add_node(
            id=f"stable_{i:02d}",
            name=f"Stable_{i}",
            revenue=random.randint(1000000, 10000000),
            time_spent=random.randint(50, 100),
            fitness=random.uniform(0.4, 0.7),
            density=random.uniform(0.3, 0.6),
            frequency=random.uniform(0.4, 0.7),
            penalty=random.uniform(0.1, 0.3),
        )
    
    # 제거 대상 (15%)
    for i in range(23):
        engine.add_node(
            id=f"removal_{i:02d}",
            name=f"Removal_{i}",
            revenue=random.randint(-1000000, 1000000),
            time_spent=random.randint(100, 200),
            fitness=random.uniform(0.1, 0.4),
            density=random.uniform(0.1, 0.3),
            frequency=random.uniform(0.1, 0.4),
            penalty=random.uniform(0.5, 1.0),
        )
    
    print(f"  총 노드: {len(engine.nodes)}명")
    
    # 리포트 생성
    print("\n[2. 3D Physics Map 리포트]")
    report = engine.generate_report()
    
    print(f"  시스템 엔트로피: {report.system_entropy:.2f}")
    print(f"  돈 생산 효율: {report.money_efficiency:.1%}")
    print(f"  현재 가치: {report.current_value:,.0f}")
    print(f"  예상 가치: {report.projected_value:,.0f}")
    print(f"  가치 배수: {report.value_multiplier:.2f}x")
    
    # 클러스터 현황
    print("\n[3. 클러스터 현황]")
    for ct, cluster in report.clusters.items():
        print(f"\n  {ct.value} ({len(cluster.nodes)}명)")
        print(f"    중심점: x={cluster.centroid[0]:.2f}, y={cluster.centroid[1]:.2f}, z={cluster.centroid[2]:.2f}")
        print(f"    평균 수익: ₩{cluster.avg_revenue:,.0f}")
        print(f"    평균 시너지: {cluster.avg_synergy:.2f}")
        print(f"    총 가치: ₩{cluster.total_value:,.0f}")
        print(f"    권장: {cluster.action_description}")
    
    # 골든 볼륨
    print("\n[4. 골든 볼륨 (상위 5인)]")
    for i, node in enumerate(report.golden_volume.nodes[:5], 1):
        action = engine.get_node_actions(node)
        grade = engine.synergy_calc.get_synergy_grade(node.z)
        print(f"  #{i} {node.name}")
        print(f"      좌표: ({node.x:.2f}, {node.y:.2f}, {node.z:.2f})")
        print(f"      수익: ₩{node.revenue:,.0f}")
        print(f"      시너지 등급: {grade}")
        print(f"      액션: {action['primary']}")
    
    # 제거 대상
    print(f"\n[5. 엔트로피 제거 대상 ({len(report.removal_targets)}명)]")
    for node in report.removal_targets[:5]:
        grade = engine.synergy_calc.get_synergy_grade(node.z)
        print(f"  × {node.name}: z={node.z:.2f} ({grade})")
    
    # 최적화 시뮬레이션
    print("\n[6. 최적화 시뮬레이션]")
    amplify_ids = [n.id for n in report.amplify_targets]
    remove_ids = [n.id for n in report.removal_targets]
    
    sim = engine.simulate_optimization(
        amplify_ids=amplify_ids,
        remove_ids=remove_ids
    )
    
    print(f"  Before:")
    print(f"    노드: {sim['before']['nodes']}, 엔트로피: {sim['before']['entropy']:.2f}")
    print(f"    효율: {sim['before']['efficiency']:.1%}, 가치: {sim['before']['value']:,.0f}")
    print(f"  After:")
    print(f"    노드: {sim['after']['nodes']}, 엔트로피: {sim['after']['entropy']:.2f}")
    print(f"    효율: {sim['after']['efficiency']:.1%}, 가치: {sim['after']['value']:,.0f}")
    print(f"  개선:")
    print(f"    엔트로피 감소: {sim['improvement']['entropy_reduction']:.2f}")
    print(f"    효율 향상: +{sim['improvement']['efficiency_gain']:.1%}")
    print(f"    가치 배수: {sim['improvement']['value_multiplier']:.2f}x")
    
    # ASCII 시각화
    print("\n[7. 3D Map 시각화 (x-z 투영)]")
    print(engine.visualize_ascii())
    
    print("\n  범례: ★=Golden ◆=Efficiency ▲=HighEnergy ●=Stable ×=Removal")
    
    print("\n" + "=" * 70)
    print("✅ 3D Physics Map Engine Test Complete")
