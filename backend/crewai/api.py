# backend/crewai/api.py
# CrewAI API (간소화)

from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Dict, Optional
from datetime import datetime
from .agents import analyze_with_crewai, rule_based_analysis

router = APIRouter(prefix="/crewai", tags=["CrewAI"])


class Node(BaseModel):
    id: str
    value: float = 0


class Motion(BaseModel):
    source: str
    target: str
    amount: float


class AnalysisRequest(BaseModel):
    nodes: List[Node]
    motions: List[Motion]


@router.post("/analyze")
async def analyze(req: AnalysisRequest):
    """CrewAI 3명 에이전트 분석"""
    nodes = [n.dict() for n in req.nodes]
    motions = [m.dict() for m in req.motions]
    
    result = analyze_with_crewai(nodes, motions)
    velocity = sum(abs(m.get('amount', 0)) for m in motions) / 30
    
    return {
        "success": result.get("success", True),
        "timestamp": datetime.now().isoformat(),
        "velocity": velocity,
        **result
    }


@router.post("/quick-delete")
async def quick_delete(req: AnalysisRequest):
    """빠른 삭제 분석"""
    nodes = [n.dict() for n in req.nodes]
    
    targets = [
        {"id": n['id'], "value": n['value'], "recommendation": "DELETE"}
        for n in nodes if n.get('value', 0) <= 0
    ]
    
    return {
        "success": True,
        "count": len(targets),
        "targets": targets,
        "monthly_savings": len(targets) * 500000
    }


@router.post("/quick-automate")
async def quick_automate(req: AnalysisRequest):
    """빠른 자동화 분석"""
    motions = [m.dict() for m in req.motions]
    
    counts = {}
    for m in motions:
        k = f"{m['source']}->{m['target']}"
        counts[k] = counts.get(k, 0) + 1
    
    targets = [
        {"motion": k, "frequency": v, "recommendation": "AUTOMATE"}
        for k, v in counts.items() if v >= 3
    ]
    
    return {
        "success": True,
        "count": len(targets),
        "targets": targets,
        "time_saved_hours": len(targets) * 5
    }


@router.get("/health")
async def health():
    """상태 확인"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}
