# backend/parasitic/api.py
# Parasitic API (실제 SaaS 연동 포함)

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from .absorber import absorber, SUPPORTED
from .saas_clients import SaaSCredentials

router = APIRouter(prefix="/parasitic", tags=["Parasitic"])


class ConnectRequest(BaseModel):
    saas_type: str


class CredentialsRequest(BaseModel):
    connector_id: str
    api_key: Optional[str] = None
    api_secret: Optional[str] = None
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    merchant_id: Optional[str] = None
    store_url: Optional[str] = None


@router.get("/supported")
async def list_supported():
    """지원 SaaS 목록"""
    return {
        "supported": [
            {
                "type": k, 
                "name": v["name"], 
                "monthly_cost": v["cost"],
                "has_api": v.get("has_api", False)
            }
            for k, v in SUPPORTED.items()
        ]
    }


@router.post("/connect")
async def connect(req: ConnectRequest):
    """연동 시작"""
    if req.saas_type not in SUPPORTED:
        raise HTTPException(status_code=400, detail=f"Unsupported SaaS: {req.saas_type}")
    
    cid = absorber.add(req.saas_type)
    result = absorber.start_parasitic(cid)
    return {"connector_id": cid, **result}


@router.post("/credentials")
async def set_credentials(req: CredentialsRequest):
    """인증 정보 설정"""
    credentials = SaaSCredentials(
        api_key=req.api_key,
        api_secret=req.api_secret,
        access_token=req.access_token,
        refresh_token=req.refresh_token,
        merchant_id=req.merchant_id,
        store_url=req.store_url
    )
    
    success = absorber.set_credentials(req.connector_id, credentials)
    if not success:
        raise HTTPException(status_code=404, detail="Connector not found")
    
    return {"success": True, "message": "Credentials set"}


@router.post("/sync/{cid}")
async def sync_data(cid: str):
    """데이터 동기화 (실제 API 호출)"""
    connector = absorber.get_connector(cid)
    if not connector:
        raise HTTPException(status_code=404, detail="Connector not found")
    
    result = await absorber.sync(cid)
    
    return {
        "success": result.success,
        "records_fetched": result.records_fetched,
        "records_transformed": result.records_transformed,
        "errors": result.errors,
        "sync_count": connector.get("sync_count", 0) + 1,
        "stage": connector.get("stage")
    }


@router.get("/connector/{cid}")
async def get_connector(cid: str):
    """커넥터 상세 정보"""
    connector = absorber.get_connector(cid)
    if not connector:
        raise HTTPException(status_code=404, detail="Connector not found")
    return connector


@router.get("/history/{cid}")
async def get_sync_history(cid: str):
    """동기화 히스토리"""
    history = absorber.get_sync_history(cid)
    return {
        "connector_id": cid,
        "history": [
            {
                "success": h.success,
                "records_fetched": h.records_fetched,
                "records_transformed": h.records_transformed,
                "timestamp": h.timestamp.isoformat()
            }
            for h in history
        ],
        "total_syncs": len(history)
    }


@router.post("/absorb/{cid}")
async def absorb(cid: str):
    """흡수 시작"""
    return absorber.absorb(cid)


@router.post("/replace/{cid}")
async def replace(cid: str):
    """대체 준비"""
    return absorber.replace(cid)


@router.post("/complete/{cid}")
async def complete(cid: str):
    """대체 완료"""
    return absorber.complete(cid)


@router.get("/status")
async def status():
    """전체 상태"""
    return absorber.get_status()


@router.get("/flywheel")
async def flywheel():
    """플라이휠 상태"""
    s = absorber.get_status()
    
    return {
        "total_connectors": s["total"],
        "by_stage": s["by_stage"],
        "monthly_savings": s["monthly_savings"],
        "annual_savings": s["annual_savings"],
        "progress": {
            "parasitic": s["by_stage"].get("parasitic", 0),
            "absorbing": s["by_stage"].get("absorbing", 0),
            "replacing": s["by_stage"].get("replacing", 0),
            "replaced": s["by_stage"].get("replaced", 0)
        }
    }
