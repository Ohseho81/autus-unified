# backend/autosync/detector.py
# SaaS 자동 감지기 (간소화)

from typing import Dict, List, Optional
from .registry import SaaSRegistry, SystemType


class AutoSyncDetector:
    """
    Zero-Input AutoSync 감지기
    
    쿠키/도메인/API키로 SaaS 자동 감지
    """
    
    def __init__(self):
        self.registry = SaaSRegistry
        self.detected: List[str] = []
    
    def detect_from_cookies(self, cookies: str) -> List[str]:
        """쿠키에서 SaaS 감지"""
        detected = []
        cookies_lower = cookies.lower()
        
        for sys_id, cfg in self.registry.SYSTEMS.items():
            patterns = cfg.get("detection", {}).get("cookies", [])
            for p in patterns:
                if p.lower() in cookies_lower:
                    detected.append(sys_id)
                    break
        
        return list(set(detected))
    
    def detect_from_domains(self, domains: List[str]) -> List[str]:
        """도메인에서 SaaS 감지"""
        detected = []
        
        for sys_id, cfg in self.registry.SYSTEMS.items():
            patterns = cfg.get("detection", {}).get("domains", [])
            for d in domains:
                for p in patterns:
                    if p in d:
                        detected.append(sys_id)
                        break
        
        return list(set(detected))
    
    def detect_from_api_key(self, key: str) -> Optional[str]:
        """API 키 패턴으로 감지"""
        for sys_id, cfg in self.registry.SYSTEMS.items():
            patterns = cfg.get("detection", {}).get("api_patterns", [])
            for p in patterns:
                if key.startswith(p):
                    return sys_id
        return None
    
    def detect_all(
        self,
        cookies: Optional[str] = None,
        domains: Optional[List[str]] = None,
        api_key: Optional[str] = None
    ) -> Dict:
        """모든 방법으로 감지"""
        detected = set()
        
        if cookies:
            detected.update(self.detect_from_cookies(cookies))
        if domains:
            detected.update(self.detect_from_domains(domains))
        if api_key:
            sys = self.detect_from_api_key(api_key)
            if sys:
                detected.add(sys)
        
        self.detected = list(detected)
        
        return {
            "detected": self.detected,
            "count": len(self.detected),
            "details": [
                {
                    "id": s,
                    "name": self.registry.SYSTEMS[s]["name"],
                    "type": self.registry.SYSTEMS[s]["type"].value
                }
                for s in self.detected
            ]
        }
    
    def get_templates(self) -> List[Dict]:
        """감지된 시스템 템플릿"""
        return [
            {
                "system_id": s,
                "name": self.registry.SYSTEMS[s].get("name"),
                "mapping": self.registry.SYSTEMS[s].get("mapping", {})
            }
            for s in self.detected
        ]


# 글로벌 인스턴스
detector = AutoSyncDetector()
