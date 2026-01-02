# backend/physics/router.py
"""
AUTUS Physics Engine Router
============================
Money Physics 엔진을 main.py에 통합하기 위한 라우터

엔드포인트:
- GET /physics/state: 현재 맵 상태
- GET /physics/kpi: KPI 조회
- GET /physics/predict: 예측
- POST /physics/event: 이벤트 추가
- POST /physics/drag: 드래그 입력
- POST /physics/person: 사람 추가
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from enum import Enum
import uuid

router = APIRouter(prefix="/physics", tags=["Physics Engine"])


# ═══════════════════════════════════════════════════════════════════════════
# Models
# ═══════════════════════════════════════════════════════════════════════════

class EventType(str, Enum):
    MINT = "mint"       # 돈 획득
    BURN = "burn"       # 돈 소비
    TRANSFER = "transfer"  # 돈 이동


class DragType(str, Enum):
    ALLOCATION = "allocation"  # 배분
    LINK = "link"              # 연결
    SWAP = "swap"              # 교환


class EventInput(BaseModel):
    """이벤트 입력"""
    event_type: str  # "mint", "burn", "transfer"
    amount: float
    minutes: float = 60
    industry_id: str = "education"
    customer_id: str = "C001"
    project_id: str = "P001"
    participants: List[str] = ["P01"]
    evidence: Optional[str] = None


class DragInput(BaseModel):
    """드래그 입력"""
    drag_type: str  # "allocation", "link", "swap"
    params: Dict = {}


class PersonInput(BaseModel):
    """사람 추가"""
    person_id: str
    name: str


class Person:
    def __init__(self, person_id: str, name: str):
        self.person_id = person_id
        self.name = name
        self.value = 0.0


class Event:
    def __init__(self, event_id: str, timestamp: datetime, event_type: EventType,
                 amount: float, minutes: float, industry_id: str, customer_id: str,
                 project_id: str, participants: List[str], evidence: Optional[str] = None):
        self.event_id = event_id
        self.timestamp = timestamp
        self.event_type = event_type
        self.amount = amount
        self.minutes = minutes
        self.industry_id = industry_id
        self.customer_id = customer_id
        self.project_id = project_id
        self.participants = participants
        self.evidence = evidence


# ═══════════════════════════════════════════════════════════════════════════
# In-Memory Physics Engine State
# ═══════════════════════════════════════════════════════════════════════════

class PhysicsState:
    """물리 엔진 상태 관리"""
    def __init__(self):
        self.persons: Dict[str, Person] = {}
        self.events: List[Event] = []
        self.links: List[dict] = []
        self.audit_log: List[dict] = []
        self._init_demo_data()
    
    def _init_demo_data(self):
        """데모 데이터 초기화"""
        demo_persons = [
            ("P01", "오세호"),
            ("P02", "김경희"),
            ("P03", "오선우"),
            ("P04", "오연우"),
            ("P05", "오은우"),
        ]
        for pid, name in demo_persons:
            self.persons[pid] = Person(pid, name)
        
        # 초기 이벤트
        demo_events = [
            ("E0001", -6, EventType.MINT, 50000000, 2400, ["P01"]),
            ("E0002", -5, EventType.MINT, 20000000, 1800, ["P02"]),
            ("E0003", -4, EventType.MINT, 35000000, 2000, ["P01", "P03"]),
            ("E0004", -3, EventType.MINT, 25000000, 1500, ["P01", "P02", "P03"]),
            ("E0005", -2, EventType.BURN, 15000000, 600, ["P04", "P05"]),
            ("E0006", -1, EventType.MINT, 18000000, 1200, ["P02", "P04"]),
        ]
        
        for eid, days_ago, etype, amount, minutes, participants in demo_events:
            event = Event(
                event_id=eid,
                timestamp=datetime.now() + timedelta(days=days_ago),
                event_type=etype,
                amount=amount,
                minutes=minutes,
                industry_id="education",
                customer_id=f"C00{abs(days_ago)}",
                project_id=f"P00{abs(days_ago)}",
                participants=participants
            )
            self._apply_event(event)
    
    def _apply_event(self, event: Event):
        """이벤트 적용"""
        self.events.append(event)
        
        # 가치 분배
        share = event.amount / len(event.participants)
        for pid in event.participants:
            if pid in self.persons:
                if event.event_type == EventType.MINT:
                    self.persons[pid].value += share
                elif event.event_type == EventType.BURN:
                    self.persons[pid].value -= share
        
        # 감사 로그
        self.audit_log.append({
            "event_id": event.event_id,
            "timestamp": event.timestamp.isoformat(),
            "type": event.event_type.value,
            "amount": event.amount,
            "participants": event.participants
        })
    
    def get_state(self) -> dict:
        """현재 상태 반환"""
        nodes = []
        for p in self.persons.values():
            nodes.append({
                "id": p.person_id,
                "name": p.name,
                "value": p.value,
                "x": hash(p.person_id) % 500,
                "y": hash(p.name) % 400
            })
        
        return {
            "nodes": nodes,
            "links": self.links,
            "total_value": sum(p.value for p in self.persons.values()),
            "synergy": self._calculate_synergy()
        }
    
    def _calculate_synergy(self) -> float:
        """시너지 계산 (n^1.1 법칙)"""
        n = len([p for p in self.persons.values() if p.value > 0])
        return round(n ** 1.1, 2) if n > 0 else 1.0
    
    def calculate_kpi(self, days: int = 7) -> dict:
        """KPI 계산"""
        cutoff = datetime.now() - timedelta(days=days)
        recent_events = [e for e in self.events if e.timestamp >= cutoff]
        
        total_mint = sum(e.amount for e in recent_events if e.event_type == EventType.MINT)
        total_burn = sum(e.amount for e in recent_events if e.event_type == EventType.BURN)
        total_minutes = sum(e.minutes for e in recent_events)
        
        return {
            "period_days": days,
            "total_mint": total_mint,
            "total_burn": total_burn,
            "net_flow": total_mint - total_burn,
            "total_minutes": total_minutes,
            "efficiency": round(total_mint / total_minutes, 2) if total_minutes > 0 else 0,
            "event_count": len(recent_events),
            "synergy": self._calculate_synergy()
        }
    
    def predict_kpi(self, horizon_days: int = 7) -> dict:
        """KPI 예측 (Rolling Horizon)"""
        current = self.calculate_kpi(days=7)
        growth_rate = 1.1  # 주간 10% 성장 가정
        
        return {
            "horizon_days": horizon_days,
            "predicted_mint": round(current["total_mint"] * growth_rate, 2),
            "predicted_synergy": round(current["synergy"] * 1.05, 2),
            "confidence": 0.75,
            "model": "rolling_average"
        }
    
    def add_person(self, person_id: str, name: str) -> dict:
        """사람 추가"""
        if person_id in self.persons:
            raise ValueError("Person already exists")
        self.persons[person_id] = Person(person_id, name)
        return {"status": "ok", "person_id": person_id}
    
    def add_event(self, event: Event) -> dict:
        """이벤트 추가"""
        self._apply_event(event)
        return {
            "status": "ok",
            "event_id": event.event_id,
            "kpi": self.calculate_kpi(days=7)
        }


# Global state instance
state = PhysicsState()


# ═══════════════════════════════════════════════════════════════════════════
# API Endpoints
# ═══════════════════════════════════════════════════════════════════════════

@router.get("/")
async def physics_root():
    """Physics Engine 정보"""
    return {
        "name": "AUTUS Physics Engine",
        "version": "1.0.0",
        "philosophy": "사람 = 노드, 돈 = 에너지, 의미 해석 금지",
        "endpoints": [
            "GET /physics/state",
            "GET /physics/kpi",
            "GET /physics/predict",
            "POST /physics/person",
            "POST /physics/event",
            "POST /physics/drag"
        ]
    }


@router.get("/state")
async def get_state():
    """현재 맵 상태 조회"""
    return state.get_state()


@router.get("/kpi")
async def get_kpi(days: int = 7):
    """KPI 조회"""
    return state.calculate_kpi(days=days)


@router.get("/predict")
async def get_prediction(horizon_days: int = 7):
    """예측 (Rolling Horizon)"""
    return state.predict_kpi(horizon_days=horizon_days)


@router.get("/audit")
async def get_audit_log():
    """Audit 로그 조회"""
    return {"log": state.audit_log}


@router.post("/person")
async def add_person(person: PersonInput):
    """사람 추가"""
    try:
        return state.add_person(person.person_id, person.name)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/event")
async def add_event(event_input: EventInput):
    """이벤트 추가"""
    event_id = f"E{len(state.events) + 1:04d}"
    
    event = Event(
        event_id=event_id,
        timestamp=datetime.now(),
        event_type=EventType(event_input.event_type),
        amount=event_input.amount,
        minutes=event_input.minutes,
        industry_id=event_input.industry_id,
        customer_id=event_input.customer_id,
        project_id=event_input.project_id,
        participants=event_input.participants,
        evidence=event_input.evidence
    )
    
    return state.add_event(event)


@router.post("/drag")
async def handle_drag(drag_input: DragInput):
    """
    드래그 입력 처리
    - 의미 해석 금지
    - 3가지 물리 입력으로만 변환
    """
    drag_type = drag_input.drag_type
    params = drag_input.params
    
    result = {
        "success": True,
        "drag_type": drag_type,
        "params": params,
        "applied_at": datetime.now().isoformat()
    }
    
    if drag_type == "allocation":
        # 배분: 한 노드에서 다른 노드들로 가치 분배
        source = params.get("source")
        targets = params.get("targets", [])
        amount = params.get("amount", 0)
        
        if source and source in state.persons and targets:
            share = amount / len(targets)
            state.persons[source].value -= amount
            for t in targets:
                if t in state.persons:
                    state.persons[t].value += share
            result["message"] = f"Allocated {amount} from {source} to {len(targets)} targets"
    
    elif drag_type == "link":
        # 연결: 두 노드 사이에 링크 생성
        source = params.get("source")
        target = params.get("target")
        if source and target:
            state.links.append({"source": source, "target": target})
            result["message"] = f"Linked {source} -> {target}"
    
    elif drag_type == "swap":
        # 교환: 두 노드의 가치 교환
        node_a = params.get("node_a")
        node_b = params.get("node_b")
        if node_a in state.persons and node_b in state.persons:
            state.persons[node_a].value, state.persons[node_b].value = \
                state.persons[node_b].value, state.persons[node_a].value
            result["message"] = f"Swapped values between {node_a} and {node_b}"
    
    # 예측 업데이트
    result["prediction"] = state.predict_kpi(horizon_days=7)
    result["current_state"] = state.get_state()
    
    return result


@router.get("/health")
async def physics_health():
    """Physics Engine 헬스 체크"""
    return {
        "status": "healthy",
        "persons": len(state.persons),
        "events": len(state.events),
        "links": len(state.links)
    }


