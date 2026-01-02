# backend/integrations/zero_meaning.py
# Zero Meaning 정제 - 의미 데이터 제거

from typing import Dict, Any, Optional
from datetime import datetime

class ZeroMeaningCleaner:
    """
    Zero Meaning 정제 모듈
    
    원칙: 숫자만 남기고, 의미(이름/설명 등) 제거
    
    허용: id, amount, timestamp
    금지: name, email, description, address 등
    """
    
    # 허용 필드 (숫자/ID만)
    ALLOWED_FIELDS = {
        # ID 계열
        "id", "customer_id", "user_id", "vendor_id", "order_id",
        "customer", "client_id", "account_id", "external_id",
        
        # 금액 계열
        "amount", "total", "total_price", "subtotal", "revenue",
        "price", "cost", "fee", "tax", "discount",
        "totalAmount", "TotalAmt", "Amount",
        
        # 시간 계열
        "created_at", "updated_at", "timestamp", "occurred_at",
        "approvedAt", "requestedAt", "TxnDate",
    }
    
    # 금지 필드 (의미 데이터)
    FORBIDDEN_FIELDS = {
        # 신원 정보
        "name", "first_name", "last_name", "full_name",
        "email", "phone", "address", "city", "state", "country", "zip",
        "billing_address", "shipping_address",
        
        # 설명/분류
        "description", "note", "notes", "memo", "comment", "comments",
        "title", "subject", "message", "body",
        "type", "category", "tag", "tags", "label", "labels",
        "status", "state", "stage",
        
        # 기타
        "company", "organization", "product_name", "sku",
        "ip_address", "user_agent", "browser",
    }
    
    # 소스별 ID 필드 매핑
    SOURCE_ID_MAP = {
        "stripe": ["customer", "id"],
        "shopify": ["customer.id", "id"],
        "quickbooks": ["CustomerRef.value", "VendorRef.value", "Id"],
        "toss": ["orderId", "paymentKey"],
        "paddle": ["customer_id", "subscription_id"],
        "unknown": ["customer_id", "user_id", "id"],
    }
    
    # 소스별 금액 필드 매핑
    SOURCE_AMOUNT_MAP = {
        "stripe": ("amount", 100),  # (필드, 나누기)
        "shopify": ("total_price", 1),
        "quickbooks": ("TotalAmt", 1),
        "toss": ("totalAmount", 1),
        "paddle": ("amount", 1),
        "unknown": ("amount", 1),
    }
    
    def cleanse(self, data: Dict[str, Any], source: str = "unknown") -> Dict[str, Any]:
        """
        원본 데이터 정제
        
        Args:
            data: 원본 웹훅 데이터
            source: 데이터 소스 (stripe, shopify 등)
        
        Returns:
            정제된 데이터 {node_id, value, timestamp}
        """
        result = {
            "node_id": None,
            "value": 0.0,
            "timestamp": datetime.now().isoformat(),
            "source": source
        }
        
        # 1. ID 추출
        result["node_id"] = self._extract_id(data, source)
        
        # 2. 금액 추출
        result["value"] = self._extract_amount(data, source)
        
        # 3. 타임스탬프 추출
        result["timestamp"] = self._extract_timestamp(data)
        
        return result
    
    def _extract_id(self, data: Dict, source: str) -> Optional[str]:
        """ID 추출"""
        id_fields = self.SOURCE_ID_MAP.get(source, self.SOURCE_ID_MAP["unknown"])
        
        for field in id_fields:
            if "." in field:
                # 중첩 필드 (예: customer.id)
                parts = field.split(".")
                value = data
                for part in parts:
                    if isinstance(value, dict):
                        value = value.get(part)
                    else:
                        value = None
                        break
                if value:
                    return str(value)
            else:
                if field in data and data[field]:
                    return str(data[field])
        
        # 폴백: 아무 ID나 찾기
        for key in ["id", "customer_id", "user_id", "order_id"]:
            if key in data and data[key]:
                return str(data[key])
        
        return f"anon_{id(data)}"
    
    def _extract_amount(self, data: Dict, source: str) -> float:
        """금액 추출"""
        field, divisor = self.SOURCE_AMOUNT_MAP.get(source, ("amount", 1))
        
        # 직접 필드
        if field in data:
            return float(data[field]) / divisor
        
        # 중첩 탐색
        for key in ["amount", "total", "total_price", "totalAmount", "TotalAmt"]:
            if key in data:
                return float(data[key]) / divisor
        
        # object 내부
        if "object" in data and isinstance(data["object"], dict):
            obj = data["object"]
            for key in ["amount", "total"]:
                if key in obj:
                    return float(obj[key]) / divisor
        
        return 0.0
    
    def _extract_timestamp(self, data: Dict) -> str:
        """타임스탬프 추출"""
        for key in ["created_at", "updated_at", "timestamp", "approvedAt", "TxnDate"]:
            if key in data and data[key]:
                return str(data[key])
        
        return datetime.now().isoformat()
    
    def is_forbidden(self, field: str) -> bool:
        """금지 필드 여부"""
        return field.lower() in {f.lower() for f in self.FORBIDDEN_FIELDS}
    
    def remove_forbidden(self, data: Dict) -> Dict:
        """금지 필드 제거 (디버깅용)"""
        return {
            k: v for k, v in data.items()
            if not self.is_forbidden(k)
        }

# backend/integrations/zero_meaning.py
# Zero Meaning 정제 - 의미 데이터 제거

from typing import Dict, Any, Optional
from datetime import datetime

class ZeroMeaningCleaner:
    """
    Zero Meaning 정제 모듈
    
    원칙: 숫자만 남기고, 의미(이름/설명 등) 제거
    
    허용: id, amount, timestamp
    금지: name, email, description, address 등
    """
    
    # 허용 필드 (숫자/ID만)
    ALLOWED_FIELDS = {
        # ID 계열
        "id", "customer_id", "user_id", "vendor_id", "order_id",
        "customer", "client_id", "account_id", "external_id",
        
        # 금액 계열
        "amount", "total", "total_price", "subtotal", "revenue",
        "price", "cost", "fee", "tax", "discount",
        "totalAmount", "TotalAmt", "Amount",
        
        # 시간 계열
        "created_at", "updated_at", "timestamp", "occurred_at",
        "approvedAt", "requestedAt", "TxnDate",
    }
    
    # 금지 필드 (의미 데이터)
    FORBIDDEN_FIELDS = {
        # 신원 정보
        "name", "first_name", "last_name", "full_name",
        "email", "phone", "address", "city", "state", "country", "zip",
        "billing_address", "shipping_address",
        
        # 설명/분류
        "description", "note", "notes", "memo", "comment", "comments",
        "title", "subject", "message", "body",
        "type", "category", "tag", "tags", "label", "labels",
        "status", "state", "stage",
        
        # 기타
        "company", "organization", "product_name", "sku",
        "ip_address", "user_agent", "browser",
    }
    
    # 소스별 ID 필드 매핑
    SOURCE_ID_MAP = {
        "stripe": ["customer", "id"],
        "shopify": ["customer.id", "id"],
        "quickbooks": ["CustomerRef.value", "VendorRef.value", "Id"],
        "toss": ["orderId", "paymentKey"],
        "paddle": ["customer_id", "subscription_id"],
        "unknown": ["customer_id", "user_id", "id"],
    }
    
    # 소스별 금액 필드 매핑
    SOURCE_AMOUNT_MAP = {
        "stripe": ("amount", 100),  # (필드, 나누기)
        "shopify": ("total_price", 1),
        "quickbooks": ("TotalAmt", 1),
        "toss": ("totalAmount", 1),
        "paddle": ("amount", 1),
        "unknown": ("amount", 1),
    }
    
    def cleanse(self, data: Dict[str, Any], source: str = "unknown") -> Dict[str, Any]:
        """
        원본 데이터 정제
        
        Args:
            data: 원본 웹훅 데이터
            source: 데이터 소스 (stripe, shopify 등)
        
        Returns:
            정제된 데이터 {node_id, value, timestamp}
        """
        result = {
            "node_id": None,
            "value": 0.0,
            "timestamp": datetime.now().isoformat(),
            "source": source
        }
        
        # 1. ID 추출
        result["node_id"] = self._extract_id(data, source)
        
        # 2. 금액 추출
        result["value"] = self._extract_amount(data, source)
        
        # 3. 타임스탬프 추출
        result["timestamp"] = self._extract_timestamp(data)
        
        return result
    
    def _extract_id(self, data: Dict, source: str) -> Optional[str]:
        """ID 추출"""
        id_fields = self.SOURCE_ID_MAP.get(source, self.SOURCE_ID_MAP["unknown"])
        
        for field in id_fields:
            if "." in field:
                # 중첩 필드 (예: customer.id)
                parts = field.split(".")
                value = data
                for part in parts:
                    if isinstance(value, dict):
                        value = value.get(part)
                    else:
                        value = None
                        break
                if value:
                    return str(value)
            else:
                if field in data and data[field]:
                    return str(data[field])
        
        # 폴백: 아무 ID나 찾기
        for key in ["id", "customer_id", "user_id", "order_id"]:
            if key in data and data[key]:
                return str(data[key])
        
        return f"anon_{id(data)}"
    
    def _extract_amount(self, data: Dict, source: str) -> float:
        """금액 추출"""
        field, divisor = self.SOURCE_AMOUNT_MAP.get(source, ("amount", 1))
        
        # 직접 필드
        if field in data:
            return float(data[field]) / divisor
        
        # 중첩 탐색
        for key in ["amount", "total", "total_price", "totalAmount", "TotalAmt"]:
            if key in data:
                return float(data[key]) / divisor
        
        # object 내부
        if "object" in data and isinstance(data["object"], dict):
            obj = data["object"]
            for key in ["amount", "total"]:
                if key in obj:
                    return float(obj[key]) / divisor
        
        return 0.0
    
    def _extract_timestamp(self, data: Dict) -> str:
        """타임스탬프 추출"""
        for key in ["created_at", "updated_at", "timestamp", "approvedAt", "TxnDate"]:
            if key in data and data[key]:
                return str(data[key])
        
        return datetime.now().isoformat()
    
    def is_forbidden(self, field: str) -> bool:
        """금지 필드 여부"""
        return field.lower() in {f.lower() for f in self.FORBIDDEN_FIELDS}
    
    def remove_forbidden(self, data: Dict) -> Dict:
        """금지 필드 제거 (디버깅용)"""
        return {
            k: v for k, v in data.items()
            if not self.is_forbidden(k)
        }


