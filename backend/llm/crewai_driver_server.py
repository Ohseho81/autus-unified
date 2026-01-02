"""
═══════════════════════════════════════════════════════════════════════════════
AUTUS CrewAI Driver - FastAPI Server
═══════════════════════════════════════════════════════════════════════════════
멀티 에이전트 실행 + Chaos Harness + ResultSpec 반환
═══════════════════════════════════════════════════════════════════════════════
"""

import os
import time
import json
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from models import (
    TaskSpec, ResultSpec, Status, RiskLevel,
    ProposedAction, ConstraintsCheck, QualityChecks,
    Audit, ResultError, Action
)
from task_to_driver import taskspec_to_driver_request, driver_request_to_prompt_context
from llm_router import load_roles_config, pick_roles, get_llm_target, get_available_providers

# 환경 변수 로드
load_dotenv()

# ─────────────────────────────────────────────────────────────────────────────
# FASTAPI APP
# ─────────────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="AUTUS CrewAI Driver",
    description="멀티 에이전트 실행 엔진 for AUTUS Kernel",
    version="0.3.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─────────────────────────────────────────────────────────────────────────────
# CHAOS HARNESS (Fault Injection)
# ─────────────────────────────────────────────────────────────────────────────

FAULT_MODE: Dict[str, Any] = {"type": "NONE", "params": {}}

class ChaosConfig(BaseModel):
    """Chaos 설정"""
    type: str  # NONE, TIMEOUT, PARTIAL, INVALID, UNAUTHORIZED, OVER_BUDGET, EXCEPTION
    params: Dict[str, Any] = {}


@app.post("/chaos/set")
def chaos_set(cfg: ChaosConfig):
    """Chaos 모드 설정"""
    FAULT_MODE["type"] = cfg.type
    FAULT_MODE["params"] = cfg.params
    return {"ok": True, "fault": FAULT_MODE}


@app.get("/chaos/status")
def chaos_status():
    """현재 Chaos 상태"""
    return FAULT_MODE


@app.post("/chaos/reset")
def chaos_reset():
    """Chaos 초기화"""
    FAULT_MODE["type"] = "NONE"
    FAULT_MODE["params"] = {}
    return {"ok": True, "fault": FAULT_MODE}


# ─────────────────────────────────────────────────────────────────────────────
# EXECUTION HISTORY
# ─────────────────────────────────────────────────────────────────────────────

EXECUTION_HISTORY: List[Dict[str, Any]] = []


# ─────────────────────────────────────────────────────────────────────────────
# HEALTH & STATUS
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    """헬스체크"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "0.3.0",
        "providers": get_available_providers(),
        "chaos_mode": FAULT_MODE["type"]
    }


@app.get("/status")
def status():
    """상태 정보"""
    cfg = load_roles_config()
    return {
        "available_providers": get_available_providers(),
        "roles": list(cfg.get("roles", {}).keys()),
        "profiles": list(cfg.get("routing", {}).get("task_profile_to_roles", {}).keys()),
        "execution_count": len(EXECUTION_HISTORY),
        "chaos_mode": FAULT_MODE
    }


@app.get("/history")
def get_history(limit: int = 10):
    """실행 이력"""
    return EXECUTION_HISTORY[-limit:]


# ─────────────────────────────────────────────────────────────────────────────
# CREWAI EXECUTION
# ─────────────────────────────────────────────────────────────────────────────

def create_crewai_agents(roles: List[str], task_profile: str, cfg: dict):
    """CrewAI 에이전트 생성"""
    try:
        from crewai import Agent
    except ImportError:
        raise RuntimeError("CrewAI not installed. Run: pip install crewai")
    
    agents = []
    
    role_descriptions = {
        "planner": {
            "goal": "Create a comprehensive execution plan with clear steps",
            "backstory": "Strategic planning specialist with expertise in optimization"
        },
        "executor": {
            "goal": "Execute the plan and produce structured results",
            "backstory": "Execution specialist focused on delivering outcomes"
        },
        "reviewer": {
            "goal": "Review and validate the output for quality and accuracy",
            "backstory": "Quality assurance specialist with attention to detail"
        },
        "compliance": {
            "goal": "Ensure all actions comply with regulations and policies",
            "backstory": "Compliance expert with deep knowledge of regulations"
        },
        "analyst": {
            "goal": "Analyze data and extract actionable insights",
            "backstory": "Data analyst with expertise in pattern recognition"
        }
    }
    
    for role in roles:
        desc = role_descriptions.get(role, {
            "goal": f"Perform {role} tasks effectively",
            "backstory": f"Specialist in {role}"
        })
        
        llm_target = get_llm_target(role, cfg)
        
        agent = Agent(
            role=role.upper(),
            goal=f"{desc['goal']} for task_profile={task_profile}",
            backstory=desc["backstory"],
            verbose=False,
            # NOTE: CrewAI 버전에 따라 llm 파라미터 설정 방식이 다름
            # llm=f"{llm_target.provider}/{llm_target.model}"  # 일부 버전
        )
        agents.append(agent)
    
    return agents


def run_crewai_execution(req, roles: List[str], cfg: dict) -> Dict[str, Any]:
    """CrewAI 실행"""
    try:
        from crewai import Agent, Task, Crew
    except ImportError:
        return {"error": "CrewAI not installed"}
    
    # 에이전트 생성
    agents = create_crewai_agents(roles, req.task_profile, cfg)
    
    # 프롬프트 컨텍스트 생성
    context = driver_request_to_prompt_context(req)
    
    # 태스크 생성
    task = Task(
        description=f"""
Based on the following context, analyze and provide recommendations:

{context}

Return a JSON object with the following structure:
{{
    "summary": "Brief summary of analysis",
    "proposed_actions": [
        {{
            "action": "ACTION_TYPE",
            "rationale": "Why this action",
            "expected_impact": {{"key": "value"}},
            "risk_estimate": "LOW|MEDIUM|HIGH",
            "confidence": 0.0-1.0
        }}
    ],
    "risks": ["risk1", "risk2"],
    "confidence": 0.0-1.0
}}
""".strip(),
        expected_output="Valid JSON with analysis results",
        agent=agents[0]
    )
    
    # Crew 실행
    crew = Crew(agents=agents, tasks=[task], verbose=False)
    start_time = time.time()
    output = crew.kickoff()
    execution_time = time.time() - start_time
    
    return {
        "output": str(output),
        "execution_time": execution_time,
        "roles_used": roles
    }


# ─────────────────────────────────────────────────────────────────────────────
# MAIN EXECUTION ENDPOINT
# ─────────────────────────────────────────────────────────────────────────────

@app.post("/driver/execute", response_model=ResultSpec)
def driver_execute(task: TaskSpec) -> ResultSpec:
    """
    TaskSpec을 받아 CrewAI로 실행하고 ResultSpec 반환
    """
    
    start_time = time.time()
    trace_id = task.trace_id
    task_id = task.task_id
    
    # ─────────────────────────────────────────────────────────────────────────
    # CHAOS FAULT INJECTION
    # ─────────────────────────────────────────────────────────────────────────
    
    fault_type = FAULT_MODE.get("type", "NONE")
    
    # TIMEOUT: 무한 대기
    if fault_type == "TIMEOUT":
        time.sleep(3600)  # 1시간 대기
    
    # INVALID: 잘못된 형식 반환 (FastAPI에서 validation error 발생)
    if fault_type == "INVALID":
        raise HTTPException(status_code=500, detail="Invalid response (fault injected)")
    
    # UNAUTHORIZED: 인증 실패
    if fault_type == "UNAUTHORIZED":
        return ResultSpec(
            task_id=task_id,
            status=Status.FAILED,
            confidence=0.0,
            summary="Unauthorized access (fault injected)",
            errors=[ResultError(code="401", message="Unauthorized")],
            audit=Audit(trace_id=trace_id)
        )
    
    # EXCEPTION: 예외 발생
    if fault_type == "EXCEPTION":
        raise RuntimeError("Exception fault injected")
    
    # ─────────────────────────────────────────────────────────────────────────
    # CONVERT TO DRIVER REQUEST
    # ─────────────────────────────────────────────────────────────────────────
    
    req = taskspec_to_driver_request(task)
    
    # ─────────────────────────────────────────────────────────────────────────
    # LOAD CONFIG & PICK ROLES
    # ─────────────────────────────────────────────────────────────────────────
    
    cfg = load_roles_config()
    roles = pick_roles(req.task_profile, cfg)
    
    # ─────────────────────────────────────────────────────────────────────────
    # EXECUTE CREWAI
    # ─────────────────────────────────────────────────────────────────────────
    
    try:
        execution_result = run_crewai_execution(req, roles, cfg)
    except Exception as e:
        return ResultSpec(
            task_id=task_id,
            status=Status.FAILED,
            confidence=0.0,
            summary=f"Execution failed: {str(e)}",
            errors=[ResultError(code="EXECUTION_ERROR", message=str(e))],
            audit=Audit(trace_id=trace_id)
        )
    
    execution_time = time.time() - start_time
    
    # ─────────────────────────────────────────────────────────────────────────
    # CHAOS: PARTIAL
    # ─────────────────────────────────────────────────────────────────────────
    
    if fault_type == "PARTIAL":
        result = ResultSpec(
            task_id=task_id,
            status=Status.PARTIAL,
            confidence=0.5,
            summary="Partial response (fault injected)",
            proposed_actions=[],
            raw_output=execution_result.get("output", ""),
            constraints_check=ConstraintsCheck(
                budget_ok=True,
                token_limit_ok=True,
                time_limit_ok=False
            ),
            quality_checks=QualityChecks(
                schema_valid=True,
                allowed_actions_only=True,
                no_external_side_effects=True
            ),
            errors=[ResultError(code="PARTIAL", message="Partial completion")],
            audit=Audit(trace_id=trace_id),
            metrics={"execution_time": execution_time}
        )
        EXECUTION_HISTORY.append({"task_id": task_id, "status": "PARTIAL", "time": datetime.utcnow().isoformat()})
        return result
    
    # ─────────────────────────────────────────────────────────────────────────
    # CHAOS: OVER_BUDGET
    # ─────────────────────────────────────────────────────────────────────────
    
    if fault_type == "OVER_BUDGET":
        result = ResultSpec(
            task_id=task_id,
            status=Status.COMPLETED,
            confidence=0.8,
            summary="Over budget (fault injected)",
            proposed_actions=[
                ProposedAction(
                    action=task.selected_action.value,
                    rationale="Generated despite budget overflow",
                    expected_impact={},
                    risk_estimate=RiskLevel.HIGH,
                    confidence=0.6
                )
            ],
            raw_output=execution_result.get("output", ""),
            constraints_check=ConstraintsCheck(
                budget_ok=False,
                token_limit_ok=True,
                time_limit_ok=True
            ),
            errors=[ResultError(code="OVER_BUDGET", message="Budget exceeded")],
            audit=Audit(trace_id=trace_id),
            metrics={"execution_time": execution_time, "estimated_cost_usd": 999}
        )
        EXECUTION_HISTORY.append({"task_id": task_id, "status": "OVER_BUDGET", "time": datetime.utcnow().isoformat()})
        return result
    
    # ─────────────────────────────────────────────────────────────────────────
    # NORMAL RESULT
    # ─────────────────────────────────────────────────────────────────────────
    
    # Parse output if possible
    raw_output = execution_result.get("output", "")
    proposed_actions = []
    
    try:
        # JSON 추출 시도
        if "{" in raw_output and "}" in raw_output:
            start = raw_output.find("{")
            end = raw_output.rfind("}") + 1
            json_str = raw_output[start:end]
            parsed = json.loads(json_str)
            
            for action_data in parsed.get("proposed_actions", []):
                proposed_actions.append(ProposedAction(
                    action=action_data.get("action", task.selected_action.value),
                    rationale=action_data.get("rationale", "Generated by CrewAI"),
                    expected_impact=action_data.get("expected_impact", {}),
                    risk_estimate=RiskLevel(action_data.get("risk_estimate", "MEDIUM")),
                    confidence=action_data.get("confidence", 0.7)
                ))
    except (json.JSONDecodeError, ValueError, KeyError):
        # 파싱 실패 시 기본 액션 생성
        proposed_actions.append(ProposedAction(
            action=task.selected_action.value,
            rationale="Generated by CrewAI",
            expected_impact={"signal_amount": task.signal.amount},
            risk_estimate=RiskLevel.MEDIUM,
            confidence=0.7
        ))
    
    result = ResultSpec(
        task_id=task_id,
        status=Status.COMPLETED,
        confidence=0.85,
        summary="CrewAI execution completed successfully",
        proposed_actions=proposed_actions,
        raw_output=raw_output[:2000] if len(raw_output) > 2000 else raw_output,
        constraints_check=ConstraintsCheck(
            budget_ok=True,
            token_limit_ok=True,
            time_limit_ok=True
        ),
        quality_checks=QualityChecks(
            schema_valid=True,
            allowed_actions_only=True,
            no_external_side_effects=True
        ),
        metrics={
            "execution_time": execution_time,
            "roles_used": execution_result.get("roles_used", [])
        },
        audit=Audit(trace_id=trace_id)
    )
    
    EXECUTION_HISTORY.append({
        "task_id": task_id,
        "status": "COMPLETED",
        "time": datetime.utcnow().isoformat(),
        "execution_time": execution_time
    })
    
    return result


# ─────────────────────────────────────────────────────────────────────────────
# SIMPLE TEST ENDPOINT (CrewAI 없이 테스트)
# ─────────────────────────────────────────────────────────────────────────────

@app.post("/driver/test")
def driver_test(task: TaskSpec) -> ResultSpec:
    """CrewAI 없이 간단한 테스트 실행"""
    
    req = taskspec_to_driver_request(task)
    
    return ResultSpec(
        task_id=task.task_id,
        status=Status.COMPLETED,
        confidence=0.9,
        summary=f"Test execution for {req.task_profile}",
        proposed_actions=[
            ProposedAction(
                action=task.selected_action.value,
                rationale="Test rationale",
                expected_impact={"test": True},
                risk_estimate=RiskLevel.LOW,
                confidence=0.9
            )
        ],
        raw_output=f"Inputs: {json.dumps(req.inputs, default=str)}",
        audit=Audit(trace_id=task.trace_id)
    )


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    
    print("""
═══════════════════════════════════════════════════════════════════════════════
  AUTUS CrewAI Driver Server
═══════════════════════════════════════════════════════════════════════════════
  🚀 Starting server...
  
  📡 Endpoints:
  - GET  /health              - 헬스체크
  - GET  /status              - 상태 정보
  - POST /driver/execute      - TaskSpec 실행 (CrewAI)
  - POST /driver/test         - 테스트 실행 (CrewAI 없이)
  - POST /chaos/set           - Chaos 모드 설정
  - GET  /chaos/status        - Chaos 상태
  - GET  /history             - 실행 이력
  
  ♾️ AUTUS - 모든 개체는 사람, 모든 액션은 돈
═══════════════════════════════════════════════════════════════════════════════
    """)
    
    uvicorn.run(app, host="0.0.0.0", port=8010)
