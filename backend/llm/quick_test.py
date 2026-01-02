#!/usr/bin/env python3
"""
═══════════════════════════════════════════════════════════════════════════════
AUTUS CrewAI Driver - Quick Test Script
═══════════════════════════════════════════════════════════════════════════════
서버 없이 로컬에서 모델과 변환 함수 테스트
═══════════════════════════════════════════════════════════════════════════════
"""

import json
from datetime import datetime

# 모델 임포트
from models import (
    TaskSpec, ResultSpec, Status, RiskLevel, Action, Engine,
    Node, Signal, Execution, Constraints, Override,
    ProposedAction, Audit
)
from task_to_driver import taskspec_to_driver_request, driver_request_to_prompt_context
from llm_router import load_roles_config, pick_roles, get_llm_target, get_available_providers


def test_taskspec_creation():
    """TaskSpec 생성 테스트"""
    print("\n" + "=" * 60)
    print("  TEST 1: TaskSpec Creation")
    print("=" * 60)
    
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
    
    print(f"✅ TaskSpec created: {task.task_id}")
    print(f"   Node: {task.node.node_id} ({task.node.node_type})")
    print(f"   Signal: {task.signal.motion_type} - ₩{task.signal.amount:,.0f}")
    print(f"   Action: {task.selected_action.value}")
    print(f"   Profile: {task.execution.profile}")
    
    return task


def test_taskspec_to_driver(task: TaskSpec):
    """TaskSpec → DriverRequest 변환 테스트"""
    print("\n" + "=" * 60)
    print("  TEST 2: TaskSpec → DriverRequest Conversion")
    print("=" * 60)
    
    req = taskspec_to_driver_request(task)
    
    print(f"✅ DriverRequest created:")
    print(f"   task_id: {req.task_id}")
    print(f"   trace_id: {req.trace_id}")
    print(f"   task_profile: {req.task_profile}")
    print(f"   inputs keys: {list(req.inputs.keys())}")
    print(f"   constraints: {req.constraints}")
    
    return req


def test_prompt_context(req):
    """프롬프트 컨텍스트 생성 테스트"""
    print("\n" + "=" * 60)
    print("  TEST 3: Prompt Context Generation")
    print("=" * 60)
    
    context = driver_request_to_prompt_context(req)
    
    print("✅ Prompt context generated:")
    print("-" * 40)
    print(context[:500] + "..." if len(context) > 500 else context)
    
    return context


def test_llm_router():
    """LLM 라우터 테스트"""
    print("\n" + "=" * 60)
    print("  TEST 4: LLM Router")
    print("=" * 60)
    
    cfg = load_roles_config()
    
    print("✅ Available providers:")
    for provider, available in get_available_providers().items():
        status = "✅" if available else "❌"
        print(f"   {status} {provider}")
    
    profiles = ["COST_OPTIMIZATION_V1", "CONTRACT_RISK_CHECK_V1", "UNKNOWN"]
    
    print("\n✅ Role routing:")
    for profile in profiles:
        roles = pick_roles(profile, cfg)
        print(f"   {profile}: {roles}")
        
        for role in roles:
            llm = get_llm_target(role, cfg)
            print(f"      └─ {role}: {llm.provider}/{llm.model}")


def test_resultspec_creation(task: TaskSpec):
    """ResultSpec 생성 테스트"""
    print("\n" + "=" * 60)
    print("  TEST 5: ResultSpec Creation")
    print("=" * 60)
    
    result = ResultSpec(
        task_id=task.task_id,
        status=Status.COMPLETED,
        confidence=0.85,
        summary="비용 누수 자동화 제안 완료",
        proposed_actions=[
            ProposedAction(
                action="AUTOMATE",
                rationale="월 1,200만원 절감 가능",
                expected_impact={"monthly_savings": 12000000},
                risk_estimate=RiskLevel.MEDIUM,
                confidence=0.85
            )
        ],
        audit=Audit(trace_id=task.trace_id)
    )
    
    print(f"✅ ResultSpec created: {result.result_id}")
    print(f"   Status: {result.status.value}")
    print(f"   Confidence: {result.confidence:.0%}")
    print(f"   Proposed Actions: {len(result.proposed_actions)}")
    print(f"   Constraints OK: budget={result.constraints_check.budget_ok}, token={result.constraints_check.token_limit_ok}")
    
    return result


def test_json_serialization(task: TaskSpec, result: ResultSpec):
    """JSON 직렬화 테스트"""
    print("\n" + "=" * 60)
    print("  TEST 6: JSON Serialization")
    print("=" * 60)
    
    task_json = task.model_dump_json(indent=2)
    result_json = result.model_dump_json(indent=2)
    
    print(f"✅ TaskSpec JSON size: {len(task_json)} bytes")
    print(f"✅ ResultSpec JSON size: {len(result_json)} bytes")
    
    # 역직렬화 테스트
    task_restored = TaskSpec.model_validate_json(task_json)
    result_restored = ResultSpec.model_validate_json(result_json)
    
    print(f"✅ TaskSpec restored: {task_restored.task_id}")
    print(f"✅ ResultSpec restored: {result_restored.result_id}")


def main():
    """메인 테스트 실행"""
    print("""
═══════════════════════════════════════════════════════════════════════════════
  AUTUS CrewAI Driver - Quick Test
═══════════════════════════════════════════════════════════════════════════════
  Testing models, conversion, and router without server
═══════════════════════════════════════════════════════════════════════════════
    """)
    
    # 테스트 실행
    task = test_taskspec_creation()
    req = test_taskspec_to_driver(task)
    test_prompt_context(req)
    test_llm_router()
    result = test_resultspec_creation(task)
    test_json_serialization(task, result)
    
    print("\n" + "=" * 60)
    print("  ALL TESTS PASSED! ✅")
    print("=" * 60)
    print("\n  Next: Run the server with `python crewai_driver_server.py`")
    print("  Then: Run chaos tests with `python chaos_runner.py`")
    print()


if __name__ == "__main__":
    main()
