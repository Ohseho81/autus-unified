# backend/crewai/agents.py
# CrewAI 3명 에이전트 (간소화)

from typing import Dict, List, Any
import os

# CrewAI 지연 로딩
_crewai_available = False
try:
    from crewai import Agent, Task, Crew, Process
    _crewai_available = True
except ImportError:
    pass


def get_llm():
    """LLM 설정 (Claude > GPT > Groq)"""
    try:
        from langchain_anthropic import ChatAnthropic
        if os.getenv("ANTHROPIC_API_KEY"):
            return ChatAnthropic(model="claude-3-5-sonnet-20241022")
    except:
        pass
    
    try:
        from langchain_openai import ChatOpenAI
        if os.getenv("OPENAI_API_KEY"):
            return ChatOpenAI(model="gpt-4o")
    except:
        pass
    
    return None


def analyze_with_crewai(nodes: List[Dict], motions: List[Dict]) -> Dict:
    """CrewAI 분석 (사용 가능할 때)"""
    if not _crewai_available:
        return rule_based_analysis(nodes, motions)
    
    llm = get_llm()
    if not llm:
        return rule_based_analysis(nodes, motions)
    
    # 에이전트 생성
    delete_agent = Agent(
        role="삭제 전문가",
        goal="가치 ≤ 0 노드 제거",
        backstory="돈 유출을 무자비하게 차단",
        llm=llm, verbose=False
    )
    
    automate_agent = Agent(
        role="자동화 전문가",
        goal="반복 모션 자동화",
        backstory="시간 비용 T → 0",
        llm=llm, verbose=False
    )
    
    outsource_agent = Agent(
        role="외부용역 전문가",
        goal="고가치 노드 도입",
        backstory="ROI > 300% 도입",
        llm=llm, verbose=False
    )
    
    # 데이터 요약
    summary = create_summary(nodes, motions)
    
    # 태스크
    tasks = [
        Task(
            description=f"분석: {summary}\n가치≤0 노드 삭제 제안 (JSON)",
            expected_output="삭제 대상 JSON",
            agent=delete_agent
        ),
        Task(
            description=f"분석: {summary}\n반복 모션 자동화 제안 (JSON)",
            expected_output="자동화 대상 JSON",
            agent=automate_agent
        ),
        Task(
            description=f"분석: {summary}\n외부용역 도입 제안 (JSON)",
            expected_output="추천 JSON",
            agent=outsource_agent
        )
    ]
    
    crew = Crew(
        agents=[delete_agent, automate_agent, outsource_agent],
        tasks=tasks,
        process=Process.sequential,
        verbose=False
    )
    
    try:
        result = crew.kickoff()
        return {"success": True, "analysis": str(result)}
    except Exception as e:
        return {"success": False, "error": str(e), "fallback": rule_based_analysis(nodes, motions)}


def create_summary(nodes: List[Dict], motions: List[Dict]) -> str:
    """LLM용 데이터 요약"""
    total = sum(n.get('value', 0) for n in nodes)
    low_value = [n for n in nodes if n.get('value', 0) <= 0]
    
    return f"노드 {len(nodes)}개, 총 가치 ₩{total:,.0f}, 저가치 {len(low_value)}개"


def rule_based_analysis(nodes: List[Dict], motions: List[Dict]) -> Dict:
    """규칙 기반 분석 (CrewAI 없을 때)"""
    
    # 삭제 대상
    delete_targets = [
        {"id": n.get('id'), "value": n.get('value', 0)}
        for n in nodes if n.get('value', 0) <= 0
    ]
    
    # 자동화 대상
    motion_counts = {}
    for m in motions:
        k = f"{m.get('source')}->{m.get('target')}"
        motion_counts[k] = motion_counts.get(k, 0) + 1
    
    automate_targets = [
        {"motion": k, "frequency": v}
        for k, v in motion_counts.items() if v >= 3
    ]
    
    # 예상 효과
    monthly_savings = len(delete_targets) * 500000
    monthly_synergy = len(automate_targets) * 1000000
    monthly_accel = 3000000
    
    return {
        "success": True,
        "delete": {"targets": delete_targets, "monthly_savings": monthly_savings},
        "automate": {"targets": automate_targets, "monthly_synergy_gain": monthly_synergy},
        "outsource": {
            "recommendations": [
                {"role": "마케팅 전문가", "roi": 300},
                {"role": "영업 전문가", "roi": 250}
            ],
            "monthly_acceleration": monthly_accel
        },
        "total_monthly_impact": monthly_savings + monthly_synergy + monthly_accel
    }
