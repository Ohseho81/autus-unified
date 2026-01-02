"""
═══════════════════════════════════════════════════════════════════════════════
AUTUS CrewAI Driver - Data Models
═══════════════════════════════════════════════════════════════════════════════
TaskSpec / DriverRequest / ResultSpec / AuditEvent
AUTUS Kernel과 CrewAI Driver 간의 계약 스키마
═══════════════════════════════════════════════════════════════════════════════
"""

from pydantic import BaseModel, Field
from typing import Literal, List, Optional, Dict, Any
from datetime import datetime
from enum import Enum
import uuid


# ─────────────────────────────────────────────────────────────────────────────
# ENUMS
# ─────────────────────────────────────────────────────────────────────────────

class Action(str, Enum):
    """허용된 액션 타입"""
    DELETE = "DELETE"
    DELETE_SOFT = "DELETE_SOFT"
    DELETE_HARD = "DELETE_HARD"
    AUTOMATE = "AUTOMATE"
    OUTSOURCE = "OUTSOURCE"
    LINK = "LINK"
    CUT = "CUT"
    HOLD = "HOLD"


class Engine(str, Enum):
    """실행 엔진 타입"""
    CREWAI = "CREWAI"
    LOCAL_SCRIPT = "LOCAL_SCRIPT"
    HTTP_WEBHOOK = "HTTP_WEBHOOK"
    HUMAN_EXECUTOR = "HUMAN_EXECUTOR"


class Status(str, Enum):
    """결과 상태"""
    COMPLETED = "COMPLETED"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"
    TIMEOUT = "TIMEOUT"
    HOLD = "HOLD"
    ABORTED = "ABORTED"


class RiskLevel(str, Enum):
    """리스크 레벨"""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


# ─────────────────────────────────────────────────────────────────────────────
# NODE & SIGNAL (TaskSpec 구성요소)
# ─────────────────────────────────────────────────────────────────────────────

class Node(BaseModel):
    """노드 (사람 또는 엔티티)"""
    node_id: str
    node_type: str = "PERSON"
    name: Optional[str] = None
    metadata: Dict[str, Any] = {}


class Signal(BaseModel):
    """신호 (돈 모션)"""
    motion_type: str  # COST_LEAK, REVENUE_SURGE, SYNERGY_DROP 등
    amount: float = 0
    confidence: float = Field(ge=0, le=1, default=0.5)
    source: Optional[str] = None


# ─────────────────────────────────────────────────────────────────────────────
# CONSTRAINTS
# ─────────────────────────────────────────────────────────────────────────────

class Constraints(BaseModel):
    """실행 제약조건"""
    budget_usd: float = Field(default=5.0, ge=0)
    time_limit: str = "30m"  # 30m, 1h, etc
    token_limit: int = Field(default=8000, ge=0)
    max_retries: int = Field(default=3, ge=0)


# ─────────────────────────────────────────────────────────────────────────────
# EXECUTION CONFIG
# ─────────────────────────────────────────────────────────────────────────────

class Execution(BaseModel):
    """실행 설정"""
    engine: Engine = Engine.CREWAI
    profile: str  # COST_OPTIMIZATION_V1, CONTRACT_RISK_CHECK_V1 등
    constraints: Constraints = Constraints()


# ─────────────────────────────────────────────────────────────────────────────
# OVERRIDE (인간 승인)
# ─────────────────────────────────────────────────────────────────────────────

class OverrideDecision(BaseModel):
    """오버라이드 결정"""
    approved: bool = False
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    reason: Optional[str] = None


class Override(BaseModel):
    """오버라이드 정보"""
    override_id: Optional[str] = None
    required: bool = False
    decision: OverrideDecision = OverrideDecision()


# ─────────────────────────────────────────────────────────────────────────────
# TASKSPEC (Kernel → Driver)
# ─────────────────────────────────────────────────────────────────────────────

class TaskSpec(BaseModel):
    """
    AUTUS Kernel이 Driver에게 전달하는 태스크 명세
    """
    version: str = "2.0"
    task_id: str = Field(default_factory=lambda: f"TSK-{uuid.uuid4().hex[:8].upper()}")
    trace_id: str = Field(default_factory=lambda: f"TRACE-{uuid.uuid4().hex[:8].upper()}")
    
    # 대상 노드
    node: Node
    
    # 감지된 신호
    signal: Signal
    
    # 액션 설정
    allowed_actions: List[Action] = [Action.DELETE, Action.AUTOMATE, Action.OUTSOURCE]
    selected_action: Action
    
    # 실행 설정
    execution: Execution
    
    # 리스크 지표 (0~1)
    reversibility: float = Field(default=0.9, ge=0, le=1)
    blast_radius: float = Field(default=0.4, ge=0, le=1)
    compliance_impact: float = Field(default=0.2, ge=0, le=1)
    
    # 오버라이드
    override: Override = Override()
    
    # 메타데이터
    created_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = {}


# ─────────────────────────────────────────────────────────────────────────────
# DRIVER REQUEST (TaskSpec → Driver 변환)
# ─────────────────────────────────────────────────────────────────────────────

class DriverRequest(BaseModel):
    """
    CrewAI Driver에게 전달하는 실행 요청
    TaskSpec에서 변환됨
    """
    task_id: str
    trace_id: str
    task_profile: str
    inputs: Dict[str, Any]
    constraints: Dict[str, Any]


# ─────────────────────────────────────────────────────────────────────────────
# PROPOSED ACTION (ResultSpec 구성요소)
# ─────────────────────────────────────────────────────────────────────────────

class ProposedAction(BaseModel):
    """제안된 액션"""
    action: str
    rationale: str
    expected_impact: Dict[str, Any] = {}
    risk_estimate: RiskLevel = RiskLevel.MEDIUM
    confidence: float = Field(default=0.7, ge=0, le=1)


# ─────────────────────────────────────────────────────────────────────────────
# CONSTRAINTS CHECK
# ─────────────────────────────────────────────────────────────────────────────

class ConstraintsCheck(BaseModel):
    """제약조건 검사 결과"""
    budget_ok: bool = True
    token_limit_ok: bool = True
    time_limit_ok: bool = True


# ─────────────────────────────────────────────────────────────────────────────
# QUALITY CHECKS
# ─────────────────────────────────────────────────────────────────────────────

class QualityChecks(BaseModel):
    """품질 검사 결과"""
    schema_valid: bool = True
    allowed_actions_only: bool = True
    no_external_side_effects: bool = True


# ─────────────────────────────────────────────────────────────────────────────
# ERROR
# ─────────────────────────────────────────────────────────────────────────────

class ResultError(BaseModel):
    """에러 정보"""
    code: str
    message: Optional[str] = None
    details: Dict[str, Any] = {}


# ─────────────────────────────────────────────────────────────────────────────
# AUDIT
# ─────────────────────────────────────────────────────────────────────────────

class Audit(BaseModel):
    """감사 로그 정보"""
    trace_id: str
    immutable_log: bool = True
    logged_at: datetime = Field(default_factory=datetime.utcnow)


# ─────────────────────────────────────────────────────────────────────────────
# RESULT SPEC (Driver → Kernel)
# ─────────────────────────────────────────────────────────────────────────────

class ResultSpec(BaseModel):
    """
    CrewAI Driver가 Kernel에게 반환하는 결과 명세
    """
    version: str = "2.0"
    result_id: str = Field(default_factory=lambda: f"RES-{uuid.uuid4().hex[:8].upper()}")
    task_id: str
    
    # 상태
    status: Status
    confidence: float = Field(ge=0, le=1, default=0.5)
    
    # 결과 요약
    summary: str
    
    # 제안된 액션들
    proposed_actions: List[ProposedAction] = []
    
    # 아티팩트 (파일 경로, URL 등)
    artifacts: List[str] = []
    
    # Raw 출력 (디버깅용)
    raw_output: Optional[str] = None
    
    # 검사 결과
    constraints_check: ConstraintsCheck = ConstraintsCheck()
    quality_checks: QualityChecks = QualityChecks()
    
    # 메트릭
    metrics: Dict[str, Any] = {}
    
    # 에러
    errors: List[ResultError] = []
    
    # 감사
    audit: Audit
    
    # 타임스탬프
    created_at: datetime = Field(default_factory=datetime.utcnow)


# ─────────────────────────────────────────────────────────────────────────────
# AUDIT EVENT (전체 이력 기록)
# ─────────────────────────────────────────────────────────────────────────────

class AuditEvent(BaseModel):
    """감사 이벤트 (전체 이력)"""
    event_id: str = Field(default_factory=lambda: f"EVT-{uuid.uuid4().hex[:8].upper()}")
    trace_id: str
    task_id: str
    event_type: str  # TASK_CREATED, DRIVER_STARTED, DRIVER_COMPLETED, etc
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    payload: Dict[str, Any] = {}
    actor: Optional[str] = None  # system, user_id, driver_name


# ─────────────────────────────────────────────────────────────────────────────
# USAGE EXAMPLE
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    # TaskSpec 생성 예시
    task = TaskSpec(
        node=Node(node_id="N-23901", node_type="STORE", name="Seoul Store #1"),
        signal=Signal(motion_type="COST_LEAK", amount=12000000, confidence=0.82),
        selected_action=Action.AUTOMATE,
        execution=Execution(
            engine=Engine.CREWAI,
            profile="COST_OPTIMIZATION_V1",
            constraints=Constraints(budget_usd=5, time_limit="30m", token_limit=8000)
        )
    )
    
    print("=== TaskSpec Example ===")
    print(task.model_dump_json(indent=2))
    
    # ResultSpec 생성 예시
    result = ResultSpec(
        task_id=task.task_id,
        status=Status.COMPLETED,
        confidence=0.85,
        summary="비용 누수 자동화 제안 완료",
        proposed_actions=[
            ProposedAction(
                action="AUTOMATE",
                rationale="월 1,200만원 비용 절감 가능",
                expected_impact={"monthly_savings": 12000000},
                risk_estimate=RiskLevel.MEDIUM,
                confidence=0.85
            )
        ],
        audit=Audit(trace_id=task.trace_id)
    )
    
    print("\n=== ResultSpec Example ===")
    print(result.model_dump_json(indent=2))
