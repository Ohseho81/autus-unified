# backend/autosync/api.py
# AutoSync API (간소화)

from fastapi import APIRouter, Request
from pydantic import BaseModel
from typing import List, Dict, Optional
from datetime import datetime

from .detector import detector
from .registry import SaaSRegistry, SystemType
from .transformer import transformer, flow_detector

router = APIRouter(prefix="/autosync", tags=["AutoSync"])


class DetectRequest(BaseModel):
    cookies: Optional[str] = None
    domains: Optional[List[str]] = None
    api_key: Optional[str] = None


class TransformRequest(BaseModel):
    data: Dict
    system_id: Optional[str] = None


@router.get("/systems")
async def list_systems():
    """지원 시스템 목록"""
    systems = SaaSRegistry.get_all()
    grouped = {}
    for sys_id, cfg in systems.items():
        t = cfg["type"].value
        if t not in grouped:
            grouped[t] = []
        grouped[t].append({"id": sys_id, "name": cfg["name"]})
    return {"total": len(systems), "by_type": grouped}


@router.post("/detect")
async def detect_systems(req: DetectRequest):
    """SaaS 자동 감지"""
    result = detector.detect_all(
        cookies=req.cookies,
        domains=req.domains,
        api_key=req.api_key
    )
    result["templates"] = detector.get_templates()
    return {"success": True, **result}


@router.post("/transform")
async def transform_data(req: TransformRequest):
    """데이터 변환"""
    result = transformer.transform(req.data, req.system_id)
    result["flow_type"] = flow_detector.detect(req.data)
    return {"success": True, "transformed": result}


@router.post("/connect")
async def connect_system(system_id: str):
    """연동 시작"""
    system = SaaSRegistry.get_system(system_id)
    if not system:
        return {"success": False, "error": "Unknown system"}
    
    return {
        "success": True,
        "system": {"id": system_id, "name": system["name"]},
        "webhook_url": f"/autosync/webhook/{system_id}",
        "mapping": system.get("mapping", {})
    }


@router.post("/webhook/{system_id}")
async def webhook(system_id: str, request: Request):
    """범용 Webhook"""
    data = await request.json()
    transformed = transformer.transform(data, system_id)
    transformed["flow_type"] = flow_detector.detect(data)
    return {
        "success": True,
        "processed": transformed,
        "timestamp": datetime.now().isoformat()
    }
