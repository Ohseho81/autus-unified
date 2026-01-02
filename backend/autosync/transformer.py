# backend/autosync/transformer.py
# Universal Transformer (간소화)

from typing import Dict, Any, Optional
from datetime import datetime
from .registry import SaaSRegistry


class UniversalTransformer:
    """모든 SaaS → {node_id, value, timestamp}"""
    
    FORBIDDEN = {"name", "email", "phone", "address", "description", "note"}
    
    def transform(self, data: Dict, system_id: Optional[str] = None) -> Dict:
        mapping = SaaSRegistry.get_mapping(system_id) if system_id else None
        
        if not mapping:
            return self._generic(data)
        
        return {
            "node_id": self._get_id(data, mapping.get("node_id", [])),
            "value": self._get_value(data, mapping.get("value", [])),
            "timestamp": self._get_time(data, mapping.get("timestamp", [])),
            "source": system_id or "unknown"
        }
    
    def _get_nested(self, data: Dict, path: str) -> Any:
        for p in path.split("."):
            data = data.get(p) if isinstance(data, dict) else None
            if data is None:
                return None
        return data
    
    def _get_id(self, data: Dict, paths) -> str:
        paths = [paths] if isinstance(paths, str) else paths
        for p in paths:
            v = self._get_nested(data, p)
            if v:
                return str(v)
        for k in ["id", "customer_id", "user_id", "member_id"]:
            if k in data and data[k]:
                return str(data[k])
        return f"anon_{id(data)}"
    
    def _get_value(self, data: Dict, cfg) -> float:
        if isinstance(cfg, list) and len(cfg) >= 2:
            path, div = cfg[0], cfg[1]
        else:
            path = cfg[0] if isinstance(cfg, list) else cfg
            div = 1
        
        v = self._get_nested(data, path) if path else None
        if v:
            try:
                return float(v) / div
            except:
                pass
        
        for k in ["amount", "total", "total_price", "totalAmount"]:
            if k in data:
                try:
                    return float(data[k]) / div
                except:
                    pass
        return 0.0
    
    def _get_time(self, data: Dict, paths) -> str:
        paths = [paths] if isinstance(paths, str) else paths
        for p in paths:
            v = self._get_nested(data, p)
            if v:
                return str(v)
        for k in ["created_at", "timestamp", "date"]:
            if k in data:
                return str(data[k])
        return datetime.now().isoformat()
    
    def _generic(self, data: Dict) -> Dict:
        return {
            "node_id": self._get_id(data, []),
            "value": self._get_value(data, []),
            "timestamp": self._get_time(data, []),
            "source": "unknown"
        }


class FlowTypeDetector:
    """Flow 방향 감지"""
    
    OUTFLOW = ["refund", "cancel", "void", "chargeback", "return"]
    
    @classmethod
    def detect(cls, data: Dict) -> str:
        event = str(
            data.get("type") or data.get("event") or 
            data.get("status") or ""
        ).lower()
        
        for kw in cls.OUTFLOW:
            if kw in event:
                return "outflow"
        return "inflow"


transformer = UniversalTransformer()
flow_detector = FlowTypeDetector()
