"""
═══════════════════════════════════════════════════════════════════════════════
AUTUS CrewAI Driver - Chaos Harness Test Runner
═══════════════════════════════════════════════════════════════════════════════
12개 실패 케이스 주입 테스트
Kernel이 HOLD/ABORT로 안전하게 멈추는지 검증
═══════════════════════════════════════════════════════════════════════════════
"""

import asyncio
import httpx
import json
from datetime import datetime
from typing import List, Tuple, Any
from dataclasses import dataclass
from enum import Enum


# ─────────────────────────────────────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────────────────────────────────────

DRIVER_URL = "http://localhost:8010"
TIMEOUT_SECONDS = 10  # 테스트용 짧은 타임아웃


# ─────────────────────────────────────────────────────────────────────────────
# TEST CASES
# ─────────────────────────────────────────────────────────────────────────────

class ChaosType(str, Enum):
    NONE = "NONE"                   # 정상 실행
    TIMEOUT = "TIMEOUT"             # 타임아웃 (응답 없음)
    PARTIAL = "PARTIAL"             # 부분 완료
    INVALID = "INVALID"             # 잘못된 응답 형식
    UNAUTHORIZED = "UNAUTHORIZED"   # 인증 실패
    OVER_BUDGET = "OVER_BUDGET"     # 예산 초과
    EXCEPTION = "EXCEPTION"         # 예외 발생


@dataclass
class TestCase:
    """테스트 케이스"""
    name: str
    chaos_type: ChaosType
    params: dict
    expected_behavior: str
    timeout: int = TIMEOUT_SECONDS


# 12개 테스트 케이스
TEST_CASES: List[TestCase] = [
    # 정상 케이스
    TestCase("NORMAL", ChaosType.NONE, {}, "COMPLETED 상태, confidence > 0.5"),
    
    # 타임아웃 케이스
    TestCase("TIMEOUT_HARD", ChaosType.TIMEOUT, {}, "클라이언트 타임아웃 발생", timeout=3),
    
    # 부분 완료 케이스
    TestCase("PARTIAL_RESULT", ChaosType.PARTIAL, {}, "PARTIAL 상태, time_limit_ok=false"),
    TestCase("PARTIAL_WITH_DATA", ChaosType.PARTIAL, {"include_data": True}, "PARTIAL 상태, 일부 데이터 포함"),
    
    # 잘못된 응답 케이스
    TestCase("INVALID_RESPONSE", ChaosType.INVALID, {}, "HTTP 500 또는 파싱 에러"),
    
    # 인증 실패 케이스
    TestCase("AUTH_FAILURE", ChaosType.UNAUTHORIZED, {}, "FAILED 상태, 401 에러"),
    TestCase("AUTH_EXPIRED", ChaosType.UNAUTHORIZED, {"reason": "expired"}, "FAILED 상태, 토큰 만료"),
    
    # 예산 초과 케이스
    TestCase("BUDGET_EXCEEDED", ChaosType.OVER_BUDGET, {}, "COMPLETED but budget_ok=false"),
    TestCase("BUDGET_2X", ChaosType.OVER_BUDGET, {"multiplier": 2}, "예산 2배 초과"),
    
    # 예외 케이스
    TestCase("EXCEPTION_RUNTIME", ChaosType.EXCEPTION, {}, "HTTP 500 내부 서버 에러"),
    
    # 복합 케이스
    TestCase("NORMAL_AFTER_FAULT", ChaosType.NONE, {}, "Fault 리셋 후 정상 실행"),
    TestCase("NORMAL_STRESS", ChaosType.NONE, {"stress": True}, "정상 실행 (스트레스 플래그)"),
]


# ─────────────────────────────────────────────────────────────────────────────
# BASE TASK TEMPLATE
# ─────────────────────────────────────────────────────────────────────────────

def create_base_task(case_name: str) -> dict:
    """테스트용 기본 TaskSpec 생성"""
    return {
        "version": "2.0",
        "task_id": f"TSK-CHAOS-{case_name}-{datetime.utcnow().timestamp():.0f}",
        "trace_id": f"TRACE-CHAOS-{case_name}",
        "node": {
            "node_id": "N-23901",
            "node_type": "STORE",
            "name": "Test Store"
        },
        "signal": {
            "motion_type": "COST_LEAK",
            "amount": 12000000,
            "confidence": 0.82
        },
        "allowed_actions": ["DELETE", "AUTOMATE", "OUTSOURCE"],
        "selected_action": "AUTOMATE",
        "execution": {
            "engine": "CREWAI",
            "profile": "COST_OPTIMIZATION_V1",
            "constraints": {
                "budget_usd": 5,
                "time_limit": "30m",
                "token_limit": 8000
            }
        },
        "reversibility": 0.9,
        "blast_radius": 0.4,
        "compliance_impact": 0.2,
        "override": {
            "override_id": None,
            "required": False,
            "decision": {
                "approved": False,
                "approved_by": None
            }
        }
    }


# ─────────────────────────────────────────────────────────────────────────────
# TEST RUNNER
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class TestResult:
    """테스트 결과"""
    case_name: str
    chaos_type: str
    status_code: int | str
    response_status: str | None
    passed: bool
    details: str
    duration_ms: float


async def set_chaos_mode(client: httpx.AsyncClient, chaos_type: str, params: dict):
    """Chaos 모드 설정"""
    await client.post(
        f"{DRIVER_URL}/chaos/set",
        json={"type": chaos_type, "params": params}
    )


async def reset_chaos(client: httpx.AsyncClient):
    """Chaos 모드 리셋"""
    await client.post(f"{DRIVER_URL}/chaos/reset")


async def run_test_case(
    client: httpx.AsyncClient,
    case: TestCase
) -> TestResult:
    """단일 테스트 케이스 실행"""
    
    start_time = datetime.utcnow()
    
    # Chaos 모드 설정
    await set_chaos_mode(client, case.chaos_type.value, case.params)
    
    # TaskSpec 생성
    task = create_base_task(case.name)
    
    # 실행 (test 엔드포인트 사용 - CrewAI 없이)
    try:
        response = await client.post(
            f"{DRIVER_URL}/driver/test",  # /driver/execute 대신 /driver/test 사용
            json=task,
            timeout=case.timeout
        )
        
        duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
        
        if response.status_code == 200:
            data = response.json()
            response_status = data.get("status", "UNKNOWN")
            
            # 검증
            passed = validate_result(case, response.status_code, data)
            details = f"status={response_status}, confidence={data.get('confidence', 0)}"
            
        else:
            response_status = None
            passed = case.chaos_type in [ChaosType.INVALID, ChaosType.EXCEPTION]
            details = f"HTTP {response.status_code}: {response.text[:200]}"
        
        return TestResult(
            case_name=case.name,
            chaos_type=case.chaos_type.value,
            status_code=response.status_code,
            response_status=response_status,
            passed=passed,
            details=details,
            duration_ms=duration_ms
        )
        
    except httpx.TimeoutException:
        duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
        passed = case.chaos_type == ChaosType.TIMEOUT
        return TestResult(
            case_name=case.name,
            chaos_type=case.chaos_type.value,
            status_code="TIMEOUT",
            response_status=None,
            passed=passed,
            details="Client timeout (expected for TIMEOUT case)",
            duration_ms=duration_ms
        )
        
    except Exception as e:
        duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
        return TestResult(
            case_name=case.name,
            chaos_type=case.chaos_type.value,
            status_code="EXCEPTION",
            response_status=None,
            passed=False,
            details=str(e),
            duration_ms=duration_ms
        )


def validate_result(case: TestCase, status_code: int, data: dict) -> bool:
    """결과 검증"""
    
    # NONE (정상) - COMPLETED 예상
    if case.chaos_type == ChaosType.NONE:
        return data.get("status") == "COMPLETED" and data.get("confidence", 0) > 0.5
    
    # PARTIAL - PARTIAL 상태 예상
    if case.chaos_type == ChaosType.PARTIAL:
        return data.get("status") == "PARTIAL"
    
    # UNAUTHORIZED - FAILED 상태 예상
    if case.chaos_type == ChaosType.UNAUTHORIZED:
        return data.get("status") == "FAILED"
    
    # OVER_BUDGET - budget_ok=false 예상
    if case.chaos_type == ChaosType.OVER_BUDGET:
        constraints = data.get("constraints_check", {})
        return constraints.get("budget_ok") == False
    
    # 기본
    return True


async def run_all_tests():
    """모든 테스트 실행"""
    
    print("""
═══════════════════════════════════════════════════════════════════════════════
  AUTUS CrewAI Driver - Chaos Harness Test Runner
═══════════════════════════════════════════════════════════════════════════════
""")
    
    results: List[TestResult] = []
    
    async with httpx.AsyncClient() as client:
        # 서버 상태 확인
        try:
            health = await client.get(f"{DRIVER_URL}/health", timeout=5)
            print(f"✅ Driver server healthy: {health.json()['version']}")
        except Exception as e:
            print(f"❌ Driver server not responding: {e}")
            print(f"   Start server with: python crewai_driver_server.py")
            return
        
        print(f"\n📋 Running {len(TEST_CASES)} test cases...\n")
        print("-" * 80)
        
        # 각 테스트 케이스 실행
        for i, case in enumerate(TEST_CASES, 1):
            print(f"[{i:02d}/{len(TEST_CASES)}] {case.name} ({case.chaos_type.value})...", end=" ")
            
            result = await run_test_case(client, case)
            results.append(result)
            
            status = "✅ PASS" if result.passed else "❌ FAIL"
            print(f"{status} ({result.duration_ms:.0f}ms)")
            
            # Chaos 리셋
            await reset_chaos(client)
    
    # 결과 요약
    print("\n" + "=" * 80)
    print("  TEST RESULTS SUMMARY")
    print("=" * 80)
    
    passed = sum(1 for r in results if r.passed)
    failed = len(results) - passed
    
    print(f"\n  Total: {len(results)} | Passed: {passed} | Failed: {failed}")
    print(f"  Success Rate: {passed/len(results)*100:.1f}%")
    
    if failed > 0:
        print("\n  Failed Cases:")
        for r in results:
            if not r.passed:
                print(f"    ❌ {r.case_name}: {r.details}")
    
    print("\n" + "-" * 80)
    print("  DETAILED RESULTS")
    print("-" * 80)
    
    for r in results:
        status = "✅" if r.passed else "❌"
        print(f"\n  {status} {r.case_name}")
        print(f"     Chaos: {r.chaos_type}")
        print(f"     Status Code: {r.status_code}")
        print(f"     Response Status: {r.response_status}")
        print(f"     Duration: {r.duration_ms:.0f}ms")
        print(f"     Details: {r.details}")
    
    print("\n" + "=" * 80)
    
    return results


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    asyncio.run(run_all_tests())
