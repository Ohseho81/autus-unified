"""
═══════════════════════════════════════════════════════════════════════════════
AUTUS CrewAI Driver - TaskSpec → DriverRequest Converter
═══════════════════════════════════════════════════════════════════════════════
AUTUS Kernel의 TaskSpec을 CrewAI Driver가 실행할 수 있는 형태로 변환
═══════════════════════════════════════════════════════════════════════════════
"""

from typing import Dict, Any
from models import TaskSpec, DriverRequest


def taskspec_to_driver_request(task: TaskSpec) -> DriverRequest:
    """
    TaskSpec을 DriverRequest로 변환
    
    Args:
        task: AUTUS Kernel의 TaskSpec
        
    Returns:
        CrewAI Driver가 실행할 DriverRequest
    """
    
    # inputs: 태스크 실행에 필요한 모든 컨텍스트 정보
    inputs: Dict[str, Any] = {
        # 노드 정보
        "node_id": task.node.node_id,
        "node_type": task.node.node_type,
        "node_name": task.node.name,
        "node_metadata": task.node.metadata,
        
        # 신호 정보
        "motion_type": task.signal.motion_type,
        "amount": task.signal.amount,
        "signal_confidence": task.signal.confidence,
        "signal_source": task.signal.source,
        
        # 액션 정보
        "selected_action": task.selected_action.value,
        "allowed_actions": [a.value for a in task.allowed_actions],
        
        # 리스크 지표
        "reversibility": task.reversibility,
        "blast_radius": task.blast_radius,
        "compliance_impact": task.compliance_impact,
        
        # 오버라이드 정보
        "override": {
            "override_id": task.override.override_id,
            "required": task.override.required,
            "approved": task.override.decision.approved,
            "approved_by": task.override.decision.approved_by,
            "reason": task.override.decision.reason,
        },
        
        # 추가 메타데이터
        "metadata": task.metadata,
        "created_at": task.created_at.isoformat() if task.created_at else None,
    }
    
    # constraints: 실행 제약조건
    constraints: Dict[str, Any] = {
        "budget_usd": task.execution.constraints.budget_usd,
        "time_limit": task.execution.constraints.time_limit,
        "token_limit": task.execution.constraints.token_limit,
        "max_retries": task.execution.constraints.max_retries,
        "engine": task.execution.engine.value,
    }
    
    return DriverRequest(
        task_id=task.task_id,
        trace_id=task.trace_id,
        task_profile=task.execution.profile,
        inputs=inputs,
        constraints=constraints
    )


def driver_request_to_prompt_context(req: DriverRequest) -> str:
    """
    DriverRequest를 CrewAI 에이전트용 프롬프트 컨텍스트로 변환
    
    Args:
        req: DriverRequest
        
    Returns:
        에이전트에게 전달할 텍스트 컨텍스트
    """
    
    inputs = req.inputs
    constraints = req.constraints
    
    return f"""
═══════════════════════════════════════════════════════════════════════════════
TASK CONTEXT
═══════════════════════════════════════════════════════════════════════════════

Task ID: {req.task_id}
Trace ID: {req.trace_id}
Profile: {req.task_profile}

─────────────────────────────────────────────────────────────────────────────
TARGET NODE
─────────────────────────────────────────────────────────────────────────────
- Node ID: {inputs.get('node_id')}
- Node Type: {inputs.get('node_type')}
- Node Name: {inputs.get('node_name', 'N/A')}

─────────────────────────────────────────────────────────────────────────────
DETECTED SIGNAL
─────────────────────────────────────────────────────────────────────────────
- Motion Type: {inputs.get('motion_type')}
- Amount: {inputs.get('amount'):,.0f}
- Confidence: {inputs.get('signal_confidence', 0):.0%}

─────────────────────────────────────────────────────────────────────────────
ACTION
─────────────────────────────────────────────────────────────────────────────
- Selected Action: {inputs.get('selected_action')}
- Allowed Actions: {', '.join(inputs.get('allowed_actions', []))}

─────────────────────────────────────────────────────────────────────────────
RISK INDICATORS
─────────────────────────────────────────────────────────────────────────────
- Reversibility: {inputs.get('reversibility', 0):.0%}
- Blast Radius: {inputs.get('blast_radius', 0):.0%}
- Compliance Impact: {inputs.get('compliance_impact', 0):.0%}

─────────────────────────────────────────────────────────────────────────────
CONSTRAINTS
─────────────────────────────────────────────────────────────────────────────
- Budget: ${constraints.get('budget_usd', 0):.2f}
- Time Limit: {constraints.get('time_limit', 'N/A')}
- Token Limit: {constraints.get('token_limit', 0):,}

═══════════════════════════════════════════════════════════════════════════════
""".strip()


def parse_time_limit(time_str: str) -> int:
    """
    시간 제한 문자열을 초 단위로 변환
    
    Args:
        time_str: "30m", "1h", "90s" 등
        
    Returns:
        초 단위 정수
    """
    if not time_str:
        return 1800  # 기본 30분
    
    time_str = time_str.lower().strip()
    
    if time_str.endswith('s'):
        return int(time_str[:-1])
    elif time_str.endswith('m'):
        return int(time_str[:-1]) * 60
    elif time_str.endswith('h'):
        return int(time_str[:-1]) * 3600
    elif time_str.endswith('d'):
        return int(time_str[:-1]) * 86400
    else:
        return int(time_str)


# ─────────────────────────────────────────────────────────────────────────────
# USAGE EXAMPLE
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    from models import Node, Signal, Execution, Constraints, Engine, Action
    
    # TaskSpec 생성
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
    
    # DriverRequest로 변환
    req = taskspec_to_driver_request(task)
    
    print("=== DriverRequest ===")
    print(req.model_dump_json(indent=2))
    
    print("\n=== Prompt Context ===")
    print(driver_request_to_prompt_context(req))
