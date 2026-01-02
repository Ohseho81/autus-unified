# backend/autosync/registry/__init__.py
# 모든 시스템 레지스트리 통합

from enum import Enum
from typing import Dict, Optional

from .payment import PAYMENT_SYSTEMS
from .erp import ERP_SYSTEMS
from .crm import CRM_SYSTEMS
from .others import BOOKING_SYSTEMS, POS_SYSTEMS, ACCOUNTING_SYSTEMS


class SystemType(Enum):
    PAYMENT = "payment"
    ERP = "erp"
    CRM = "crm"
    BOOKING = "booking"
    POS = "pos"
    ACCOUNTING = "accounting"


# 타입 태깅
def _tag_type(systems: Dict, sys_type: SystemType) -> Dict:
    for k in systems:
        systems[k]["type"] = sys_type
    return systems


# 전체 시스템 병합
ALL_SYSTEMS = {
    **_tag_type(PAYMENT_SYSTEMS.copy(), SystemType.PAYMENT),
    **_tag_type(ERP_SYSTEMS.copy(), SystemType.ERP),
    **_tag_type(CRM_SYSTEMS.copy(), SystemType.CRM),
    **_tag_type(BOOKING_SYSTEMS.copy(), SystemType.BOOKING),
    **_tag_type(POS_SYSTEMS.copy(), SystemType.POS),
    **_tag_type(ACCOUNTING_SYSTEMS.copy(), SystemType.ACCOUNTING),
}


class SaaSRegistry:
    """SaaS 레지스트리 접근자"""
    
    SYSTEMS = ALL_SYSTEMS
    
    @classmethod
    def get_all(cls) -> Dict:
        return cls.SYSTEMS
    
    @classmethod
    def get_by_type(cls, sys_type: SystemType) -> Dict:
        return {k: v for k, v in cls.SYSTEMS.items() if v.get("type") == sys_type}
    
    @classmethod
    def get_mapping(cls, system_id: str) -> Optional[Dict]:
        system = cls.SYSTEMS.get(system_id)
        return system.get("mapping") if system else None
    
    @classmethod
    def get_system(cls, system_id: str) -> Optional[Dict]:
        return cls.SYSTEMS.get(system_id)
