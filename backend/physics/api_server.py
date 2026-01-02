"""
AUTUS API Server
================
FastAPI + WebSocket for Real-time Physics Map

엔드포인트:
- GET /state: 현재 맵 상태
- POST /event: 이벤트 추가
- POST /drag: 드래그 입력 처리
- WebSocket /ws: 실시간 상태 업데이트
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from pydantic import BaseModel
from typing import Dict, List, Optional, Set
from datetime import datetime
import json
import asyncio
import uvicorn

# Physics Engine import
import sys
sys.path.append('.')
from physics_engine import (
    PhysicsEngine, Event, EventType, DragType, Person
)


# ═══════════════════════════════════════════════════════════════════════════
# 1. FastAPI App 초기화
# ═══════════════════════════════════════════════════════════════════════════

app = FastAPI(
    title="AUTUS Physics Map API",
    description="SehoOS EP10 - Real-time Physics Engine",
    version="1.0.0"
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Physics Engine 인스턴스
engine = PhysicsEngine()

# WebSocket 연결 관리
class ConnectionManager:
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.add(websocket)
    
    def disconnect(self, websocket: WebSocket):
        self.active_connections.discard(websocket)
    
    async def broadcast(self, message: dict):
        """모든 연결에 상태 브로드캐스트"""
        disconnected = set()
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except:
                disconnected.add(connection)
        
        for conn in disconnected:
            self.disconnect(conn)

manager = ConnectionManager()


# ═══════════════════════════════════════════════════════════════════════════
# 2. Pydantic Models
# ═══════════════════════════════════════════════════════════════════════════

class EventInput(BaseModel):
    """이벤트 입력"""
    event_type: str  # "mint", "burn", "transfer"
    amount: float
    minutes: float
    industry_id: str = "education"
    customer_id: str = "C001"
    project_id: str = "P001"
    participants: List[str]
    evidence: Optional[str] = None


class DragInput(BaseModel):
    """드래그 입력 (물리 입력으로 변환)"""
    drag_type: str  # "allocation", "link", "swap"
    params: Dict


class PersonInput(BaseModel):
    """사람 추가"""
    person_id: str
    name: str


# ═══════════════════════════════════════════════════════════════════════════
# 3. REST Endpoints
# ═══════════════════════════════════════════════════════════════════════════

@app.get("/")
async def root():
    """API 정보"""
    return {
        "name": "AUTUS Physics Map API",
        "version": "1.0.0",
        "philosophy": "사람+돈만, 의미 해석 금지",
        "endpoints": {
            "GET /state": "현재 맵 상태",
            "GET /kpi": "KPI (7D/28D)",
            "GET /predict": "예측 (Rolling Horizon)",
            "POST /person": "사람 추가",
            "POST /event": "이벤트 추가",
            "POST /drag": "드래그 입력",
            "GET /audit": "Audit 로그",
            "WS /ws": "실시간 WebSocket"
        }
    }


@app.get("/state")
async def get_state():
    """
    현재 맵 상태
    - 사람: 점(노드) + 돈 숫자
    - 링크: 기본 숨김
    """
    return engine.get_map_state()


@app.get("/kpi")
async def get_kpi(days: int = 7):
    """KPI 조회"""
    return engine.calculate_kpi(days=days)


@app.get("/predict")
async def get_prediction(horizon_days: int = 7):
    """예측 (Rolling Horizon)"""
    return engine.predict_kpi(horizon_days=horizon_days)


@app.get("/scale")
async def get_scale_metrics():
    """Scale Law 메트릭스 (Musk Metcalfe)"""
    return engine.get_scale_metrics()


@app.get("/triggers")
async def get_triggers():
    """자동 트리거 확인"""
    return engine.check_auto_triggers()


@app.get("/audit")
async def get_audit_log():
    """Audit 로그 (JSONL)"""
    return {"log": engine.audit_log}


# ─────────────────────────────────────────────────────────────────────────
# 3.2 POST Endpoints
# ─────────────────────────────────────────────────────────────────────────

@app.post("/person")
async def add_person(person: PersonInput):
    """사람 추가"""
    if person.person_id in engine.persons:
        raise HTTPException(status_code=400, detail="Person already exists")
    
    engine.persons[person.person_id] = Person(
        person_id=person.person_id,
        name=person.name
    )
    
    # WebSocket 브로드캐스트
    await manager.broadcast({
        "type": "person_added",
        "data": {"person_id": person.person_id, "name": person.name}
    })
    
    return {"status": "ok", "person_id": person.person_id}


@app.post("/event")
async def add_event(event_input: EventInput):
    """
    이벤트 추가
    - 검증된 이벤트만 실재로 인정
    """
    event_id = f"E{len(engine.events) + 1:04d}"
    
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
    
    engine.add_event(event)
    
    # WebSocket 브로드캐스트
    state = engine.get_map_state()
    await manager.broadcast({
        "type": "state_update",
        "data": state
    })
    
    return {
        "status": "ok",
        "event_id": event_id,
        "kpi": engine.calculate_kpi(days=7)
    }


@app.post("/drag")
async def handle_drag(drag_input: DragInput):
    """
    드래그 입력 처리
    - 의미 해석 금지
    - 3가지 물리 입력으로만 변환
    """
    drag_type = DragType(drag_input.drag_type)
    result = engine.apply_drag_input(drag_type, drag_input.params)
    
    # 예측 업데이트
    prediction = engine.predict_kpi(
        horizon_days=7,
        drag_inputs=[{
            "type": drag_input.drag_type,
            "params": drag_input.params
        }]
    )
    
    result["prediction"] = prediction
    
    # WebSocket 브로드캐스트
    await manager.broadcast({
        "type": "drag_result",
        "data": result
    })
    
    return result


# ═══════════════════════════════════════════════════════════════════════════
# 4. WebSocket
# ═══════════════════════════════════════════════════════════════════════════

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    실시간 WebSocket
    - 상태 변경시 자동 브로드캐스트
    - 드래그 입력 실시간 처리
    """
    await manager.connect(websocket)
    
    try:
        # 초기 상태 전송
        await websocket.send_json({
            "type": "initial_state",
            "data": engine.get_map_state()
        })
        
        while True:
            # 클라이언트 메시지 수신
            data = await websocket.receive_json()
            
            if data.get("type") == "drag":
                # 드래그 입력 처리
                drag_type = DragType(data.get("drag_type", "allocation"))
                params = data.get("params", {})
                
                result = engine.apply_drag_input(drag_type, params)
                prediction = engine.predict_kpi(horizon_days=7)
                
                # 결과 전송 (해당 클라이언트에만)
                await websocket.send_json({
                    "type": "drag_result",
                    "data": {
                        **result,
                        "prediction": prediction
                    }
                })
            
            elif data.get("type") == "get_state":
                # 상태 요청
                await websocket.send_json({
                    "type": "state_update",
                    "data": engine.get_map_state()
                })
            
            elif data.get("type") == "ping":
                await websocket.send_json({"type": "pong"})
    
    except WebSocketDisconnect:
        manager.disconnect(websocket)


# ═══════════════════════════════════════════════════════════════════════════
# 5. 초기 데이터 로드
# ═══════════════════════════════════════════════════════════════════════════

def init_demo_data():
    """데모용 초기 데이터"""
    
    # 사람 추가
    persons = [
        ("P01", "오세호"),
        ("P02", "김경희"),
        ("P03", "오선우"),
        ("P04", "오연우"),
        ("P05", "오은우"),
    ]
    
    for pid, name in persons:
        engine.persons[pid] = Person(person_id=pid, name=name)
    
    # 초기 이벤트
    from datetime import timedelta
    
    events = [
        Event(
            event_id="E0001",
            timestamp=datetime.now() - timedelta(days=6),
            event_type=EventType.MINT,
            amount=50000000,
            minutes=2400,  # 40시간
            industry_id="education",
            customer_id="C001",
            project_id="P001",
            participants=["P01"]
        ),
        Event(
            event_id="E0002",
            timestamp=datetime.now() - timedelta(days=5),
            event_type=EventType.MINT,
            amount=20000000,
            minutes=1800,
            industry_id="education",
            customer_id="C001",
            project_id="P001",
            participants=["P02"]
        ),
        Event(
            event_id="E0003",
            timestamp=datetime.now() - timedelta(days=4),
            event_type=EventType.MINT,
            amount=35000000,
            minutes=2000,
            industry_id="education",
            customer_id="C002",
            project_id="P002",
            participants=["P01", "P03"]
        ),
        Event(
            event_id="E0004",
            timestamp=datetime.now() - timedelta(days=3),
            event_type=EventType.MINT,
            amount=25000000,
            minutes=1500,
            industry_id="education",
            customer_id="C003",
            project_id="P003",
            participants=["P01", "P02", "P03"]
        ),
        Event(
            event_id="E0005",
            timestamp=datetime.now() - timedelta(days=2),
            event_type=EventType.BURN,
            amount=15000000,
            minutes=600,
            industry_id="education",
            customer_id="C001",
            project_id="P001",
            participants=["P04", "P05"]
        ),
        Event(
            event_id="E0006",
            timestamp=datetime.now() - timedelta(days=1),
            event_type=EventType.MINT,
            amount=18000000,
            minutes=1200,
            industry_id="education",
            customer_id="C004",
            project_id="P004",
            participants=["P02", "P04"]
        ),
    ]
    
    for event in events:
        engine.add_event(event)


# 앱 시작시 초기 데이터 로드
@app.on_event("startup")
async def startup_event():
    init_demo_data()
    print("✅ AUTUS Physics Engine initialized with demo data")
    print(f"   - {len(engine.persons)} persons")
    print(f"   - {len(engine.events)} events")
    print(f"   - {len(engine.links)} links")


# ═══════════════════════════════════════════════════════════════════════════
# 6. 실행
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    uvicorn.run(
        "api_server:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
