# backend/parasitic/absorber.py
# Parasitic Absorption - 실제 SaaS 연동 포함

from typing import Dict, List, Optional
from enum import Enum
from datetime import datetime
import asyncio

from .saas_clients import (
    SaaSCredentials,
    SyncResult,
    get_saas_client,
    sync_saas_data
)


class Stage(Enum):
    PARASITIC = "parasitic"   # 기생
    ABSORBING = "absorbing"   # 흡수
    REPLACING = "replacing"   # 대체 준비
    REPLACED = "replaced"     # 완료


# 지원 SaaS
SUPPORTED = {
    "toss_pos": {"name": "토스 POS", "cost": 50000, "has_api": True},
    "kakao_pos": {"name": "카카오페이 POS", "cost": 30000, "has_api": False},
    "baemin_pos": {"name": "배민포스", "cost": 88000, "has_api": True},
    "naver_booking": {"name": "네이버예약", "cost": 30000, "has_api": True},
    "table_manager": {"name": "테이블매니저", "cost": 50000, "has_api": False},
    "gym_system": {"name": "짐앤짐", "cost": 100000, "has_api": True},
    "quickbooks": {"name": "QuickBooks", "cost": 50000, "has_api": False},
    "xero": {"name": "Xero", "cost": 40000, "has_api": False},
}


class ParasiticAbsorber:
    """기존 SaaS 기생 → 흡수 → 대체 (실제 API 연동)"""
    
    def __init__(self):
        self.connectors: Dict[str, Dict] = {}
        self.status: Dict[str, Stage] = {}
        self.credentials: Dict[str, SaaSCredentials] = {}
        self.sync_history: Dict[str, List[SyncResult]] = {}
    
    def add(self, saas_type: str, credentials: Optional[SaaSCredentials] = None) -> str:
        """연동 추가"""
        cid = f"{saas_type}_{datetime.now().strftime('%H%M%S')}"
        
        self.connectors[cid] = {
            "type": saas_type,
            "name": SUPPORTED.get(saas_type, {}).get("name", saas_type),
            "sync_count": 0,
            "last_sync": None,
            "total_records": 0,
            "created_at": datetime.now().isoformat()
        }
        self.status[cid] = Stage.PARASITIC
        self.sync_history[cid] = []
        
        if credentials:
            self.credentials[cid] = credentials
        
        return cid
    
    def set_credentials(self, cid: str, credentials: SaaSCredentials) -> bool:
        """인증 정보 설정"""
        if cid not in self.connectors:
            return False
        self.credentials[cid] = credentials
        return True
    
    async def sync(self, cid: str) -> SyncResult:
        """데이터 동기화 (실제 API 호출)"""
        if cid not in self.connectors:
            return SyncResult(success=False, errors=["Connector not found"])
        
        connector = self.connectors[cid]
        saas_type = connector["type"]
        
        # 인증 정보 확인
        credentials = self.credentials.get(cid)
        if not credentials:
            # Mock 동기화 (인증 없을 때)
            return await self._mock_sync(cid)
        
        # 실제 API 동기화
        result = await sync_saas_data(
            saas_type=saas_type,
            credentials=credentials,
            since=connector.get("last_sync")
        )
        
        if result.success:
            self.increment_sync(cid)
            connector["last_sync"] = datetime.now()
            connector["total_records"] += result.records_fetched
        
        self.sync_history[cid].append(result)
        
        return result
    
    async def _mock_sync(self, cid: str) -> SyncResult:
        """Mock 동기화 (테스트용)"""
        import random
        
        # 시뮬레이션 딜레이
        await asyncio.sleep(0.1)
        
        records = random.randint(5, 50)
        
        result = SyncResult(
            success=True,
            records_fetched=records,
            records_transformed=records
        )
        
        self.increment_sync(cid)
        self.connectors[cid]["last_sync"] = datetime.now()
        self.connectors[cid]["total_records"] += records
        self.sync_history[cid].append(result)
        
        return result
    
    def start_parasitic(self, cid: str) -> Dict:
        """기생 시작"""
        if cid not in self.connectors:
            return {"success": False, "error": "Not found"}
        
        self.status[cid] = Stage.PARASITIC
        return {
            "success": True,
            "stage": "PARASITIC",
            "message": f"기생 시작: {self.connectors[cid]['name']}",
            "next_step": "sync 메서드로 데이터 동기화"
        }
    
    def absorb(self, cid: str) -> Dict:
        """흡수 시작 (동기화 10회 이상)"""
        if cid not in self.connectors:
            return {"success": False, "error": "Not found"}
        
        c = self.connectors[cid]
        if c.get("sync_count", 0) < 10:
            return {
                "success": False, 
                "error": f"동기화 부족: {c['sync_count']}/10",
                "records_collected": c.get("total_records", 0)
            }
        
        self.status[cid] = Stage.ABSORBING
        return {
            "success": True, 
            "stage": "ABSORBING", 
            "message": "흡수 중",
            "total_records": c.get("total_records", 0)
        }
    
    def replace(self, cid: str) -> Dict:
        """대체 준비"""
        if self.status.get(cid) != Stage.ABSORBING:
            return {"success": False, "error": "흡수 미완료"}
        
        self.status[cid] = Stage.REPLACING
        saas_type = self.connectors[cid]["type"]
        cost = SUPPORTED.get(saas_type, {}).get("cost", 50000)
        
        return {
            "success": True,
            "stage": "REPLACING",
            "message": f"대체 준비 완료",
            "monthly_savings": cost,
            "action_required": "기존 SaaS 해지 준비"
        }
    
    def complete(self, cid: str) -> Dict:
        """대체 완료"""
        if self.status.get(cid) != Stage.REPLACING:
            return {"success": False, "error": "대체 준비 미완료"}
        
        self.status[cid] = Stage.REPLACED
        saas_type = self.connectors[cid]["type"]
        cost = SUPPORTED.get(saas_type, {}).get("cost", 50000)
        
        return {
            "success": True, 
            "stage": "REPLACED", 
            "message": "완전 대체!",
            "monthly_savings": cost,
            "annual_savings": cost * 12
        }
    
    def increment_sync(self, cid: str):
        """동기화 카운트 증가"""
        if cid in self.connectors:
            self.connectors[cid]["sync_count"] = self.connectors[cid].get("sync_count", 0) + 1
    
    def get_sync_history(self, cid: str) -> List[SyncResult]:
        """동기화 히스토리"""
        return self.sync_history.get(cid, [])
    
    def get_connector(self, cid: str) -> Optional[Dict]:
        """커넥터 상세 정보"""
        if cid not in self.connectors:
            return None
        
        c = self.connectors[cid]
        return {
            **c,
            "stage": self.status.get(cid, Stage.PARASITIC).value,
            "has_credentials": cid in self.credentials,
            "sync_history_count": len(self.sync_history.get(cid, []))
        }
    
    def get_status(self) -> Dict:
        """전체 상태"""
        total_savings = sum(
            SUPPORTED.get(c["type"], {}).get("cost", 0)
            for cid, c in self.connectors.items()
            if self.status.get(cid) == Stage.REPLACED
        )
        
        return {
            "connectors": {
                cid: {
                    "type": c["type"],
                    "name": c["name"],
                    "stage": self.status.get(cid, Stage.PARASITIC).value,
                    "sync_count": c.get("sync_count", 0),
                    "total_records": c.get("total_records", 0),
                    "last_sync": c.get("last_sync").isoformat() if c.get("last_sync") else None
                }
                for cid, c in self.connectors.items()
            },
            "total": len(self.connectors),
            "by_stage": {
                stage.value: len([s for s in self.status.values() if s == stage])
                for stage in Stage
            },
            "monthly_savings": total_savings,
            "annual_savings": total_savings * 12
        }


# 글로벌 인스턴스
absorber = ParasiticAbsorber()

# backend/parasitic/absorber.py
# Parasitic Absorption - 실제 SaaS 연동 포함

from typing import Dict, List, Optional
from enum import Enum
from datetime import datetime
import asyncio

from .saas_clients import (
    SaaSCredentials,
    SyncResult,
    get_saas_client,
    sync_saas_data
)


class Stage(Enum):
    PARASITIC = "parasitic"   # 기생
    ABSORBING = "absorbing"   # 흡수
    REPLACING = "replacing"   # 대체 준비
    REPLACED = "replaced"     # 완료


# 지원 SaaS
SUPPORTED = {
    "toss_pos": {"name": "토스 POS", "cost": 50000, "has_api": True},
    "kakao_pos": {"name": "카카오페이 POS", "cost": 30000, "has_api": False},
    "baemin_pos": {"name": "배민포스", "cost": 88000, "has_api": True},
    "naver_booking": {"name": "네이버예약", "cost": 30000, "has_api": True},
    "table_manager": {"name": "테이블매니저", "cost": 50000, "has_api": False},
    "gym_system": {"name": "짐앤짐", "cost": 100000, "has_api": True},
    "quickbooks": {"name": "QuickBooks", "cost": 50000, "has_api": False},
    "xero": {"name": "Xero", "cost": 40000, "has_api": False},
}


class ParasiticAbsorber:
    """기존 SaaS 기생 → 흡수 → 대체 (실제 API 연동)"""
    
    def __init__(self):
        self.connectors: Dict[str, Dict] = {}
        self.status: Dict[str, Stage] = {}
        self.credentials: Dict[str, SaaSCredentials] = {}
        self.sync_history: Dict[str, List[SyncResult]] = {}
    
    def add(self, saas_type: str, credentials: Optional[SaaSCredentials] = None) -> str:
        """연동 추가"""
        cid = f"{saas_type}_{datetime.now().strftime('%H%M%S')}"
        
        self.connectors[cid] = {
            "type": saas_type,
            "name": SUPPORTED.get(saas_type, {}).get("name", saas_type),
            "sync_count": 0,
            "last_sync": None,
            "total_records": 0,
            "created_at": datetime.now().isoformat()
        }
        self.status[cid] = Stage.PARASITIC
        self.sync_history[cid] = []
        
        if credentials:
            self.credentials[cid] = credentials
        
        return cid
    
    def set_credentials(self, cid: str, credentials: SaaSCredentials) -> bool:
        """인증 정보 설정"""
        if cid not in self.connectors:
            return False
        self.credentials[cid] = credentials
        return True
    
    async def sync(self, cid: str) -> SyncResult:
        """데이터 동기화 (실제 API 호출)"""
        if cid not in self.connectors:
            return SyncResult(success=False, errors=["Connector not found"])
        
        connector = self.connectors[cid]
        saas_type = connector["type"]
        
        # 인증 정보 확인
        credentials = self.credentials.get(cid)
        if not credentials:
            # Mock 동기화 (인증 없을 때)
            return await self._mock_sync(cid)
        
        # 실제 API 동기화
        result = await sync_saas_data(
            saas_type=saas_type,
            credentials=credentials,
            since=connector.get("last_sync")
        )
        
        if result.success:
            self.increment_sync(cid)
            connector["last_sync"] = datetime.now()
            connector["total_records"] += result.records_fetched
        
        self.sync_history[cid].append(result)
        
        return result
    
    async def _mock_sync(self, cid: str) -> SyncResult:
        """Mock 동기화 (테스트용)"""
        import random
        
        # 시뮬레이션 딜레이
        await asyncio.sleep(0.1)
        
        records = random.randint(5, 50)
        
        result = SyncResult(
            success=True,
            records_fetched=records,
            records_transformed=records
        )
        
        self.increment_sync(cid)
        self.connectors[cid]["last_sync"] = datetime.now()
        self.connectors[cid]["total_records"] += records
        self.sync_history[cid].append(result)
        
        return result
    
    def start_parasitic(self, cid: str) -> Dict:
        """기생 시작"""
        if cid not in self.connectors:
            return {"success": False, "error": "Not found"}
        
        self.status[cid] = Stage.PARASITIC
        return {
            "success": True,
            "stage": "PARASITIC",
            "message": f"기생 시작: {self.connectors[cid]['name']}",
            "next_step": "sync 메서드로 데이터 동기화"
        }
    
    def absorb(self, cid: str) -> Dict:
        """흡수 시작 (동기화 10회 이상)"""
        if cid not in self.connectors:
            return {"success": False, "error": "Not found"}
        
        c = self.connectors[cid]
        if c.get("sync_count", 0) < 10:
            return {
                "success": False, 
                "error": f"동기화 부족: {c['sync_count']}/10",
                "records_collected": c.get("total_records", 0)
            }
        
        self.status[cid] = Stage.ABSORBING
        return {
            "success": True, 
            "stage": "ABSORBING", 
            "message": "흡수 중",
            "total_records": c.get("total_records", 0)
        }
    
    def replace(self, cid: str) -> Dict:
        """대체 준비"""
        if self.status.get(cid) != Stage.ABSORBING:
            return {"success": False, "error": "흡수 미완료"}
        
        self.status[cid] = Stage.REPLACING
        saas_type = self.connectors[cid]["type"]
        cost = SUPPORTED.get(saas_type, {}).get("cost", 50000)
        
        return {
            "success": True,
            "stage": "REPLACING",
            "message": f"대체 준비 완료",
            "monthly_savings": cost,
            "action_required": "기존 SaaS 해지 준비"
        }
    
    def complete(self, cid: str) -> Dict:
        """대체 완료"""
        if self.status.get(cid) != Stage.REPLACING:
            return {"success": False, "error": "대체 준비 미완료"}
        
        self.status[cid] = Stage.REPLACED
        saas_type = self.connectors[cid]["type"]
        cost = SUPPORTED.get(saas_type, {}).get("cost", 50000)
        
        return {
            "success": True, 
            "stage": "REPLACED", 
            "message": "완전 대체!",
            "monthly_savings": cost,
            "annual_savings": cost * 12
        }
    
    def increment_sync(self, cid: str):
        """동기화 카운트 증가"""
        if cid in self.connectors:
            self.connectors[cid]["sync_count"] = self.connectors[cid].get("sync_count", 0) + 1
    
    def get_sync_history(self, cid: str) -> List[SyncResult]:
        """동기화 히스토리"""
        return self.sync_history.get(cid, [])
    
    def get_connector(self, cid: str) -> Optional[Dict]:
        """커넥터 상세 정보"""
        if cid not in self.connectors:
            return None
        
        c = self.connectors[cid]
        return {
            **c,
            "stage": self.status.get(cid, Stage.PARASITIC).value,
            "has_credentials": cid in self.credentials,
            "sync_history_count": len(self.sync_history.get(cid, []))
        }
    
    def get_status(self) -> Dict:
        """전체 상태"""
        total_savings = sum(
            SUPPORTED.get(c["type"], {}).get("cost", 0)
            for cid, c in self.connectors.items()
            if self.status.get(cid) == Stage.REPLACED
        )
        
        return {
            "connectors": {
                cid: {
                    "type": c["type"],
                    "name": c["name"],
                    "stage": self.status.get(cid, Stage.PARASITIC).value,
                    "sync_count": c.get("sync_count", 0),
                    "total_records": c.get("total_records", 0),
                    "last_sync": c.get("last_sync").isoformat() if c.get("last_sync") else None
                }
                for cid, c in self.connectors.items()
            },
            "total": len(self.connectors),
            "by_stage": {
                stage.value: len([s for s in self.status.values() if s == stage])
                for stage in Stage
            },
            "monthly_savings": total_savings,
            "annual_savings": total_savings * 12
        }


# 글로벌 인스턴스
absorber = ParasiticAbsorber()


