# backend/parasitic/saas_clients.py
# 실제 SaaS API 클라이언트

import os
import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime
from abc import ABC, abstractmethod

import httpx
from pydantic import BaseModel


class SaaSCredentials(BaseModel):
    """SaaS 인증 정보"""
    api_key: Optional[str] = None
    api_secret: Optional[str] = None
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    merchant_id: Optional[str] = None
    store_url: Optional[str] = None


class SyncResult(BaseModel):
    """동기화 결과"""
    success: bool
    records_fetched: int = 0
    records_transformed: int = 0
    errors: List[str] = []
    timestamp: datetime = datetime.now()


class BaseSaaSClient(ABC):
    """SaaS 클라이언트 베이스"""
    
    def __init__(self, credentials: SaaSCredentials):
        self.credentials = credentials
        self.http_client = httpx.AsyncClient(timeout=30.0)
    
    @abstractmethod
    async def fetch_transactions(self, since: Optional[datetime] = None) -> List[Dict]:
        """거래 데이터 조회"""
        pass
    
    @abstractmethod
    async def fetch_customers(self) -> List[Dict]:
        """고객 데이터 조회"""
        pass
    
    @abstractmethod
    def transform_to_node(self, data: Dict) -> Dict:
        """AUTUS 노드 형식으로 변환"""
        pass
    
    async def close(self):
        await self.http_client.aclose()


class TossPOSClient(BaseSaaSClient):
    """토스 POS API 클라이언트"""
    
    BASE_URL = "https://api.tosspayments.com"
    
    async def _get_headers(self) -> Dict:
        import base64
        auth = base64.b64encode(f"{self.credentials.api_key}:".encode()).decode()
        return {
            "Authorization": f"Basic {auth}",
            "Content-Type": "application/json"
        }
    
    async def fetch_transactions(self, since: Optional[datetime] = None) -> List[Dict]:
        """토스 결제 내역 조회"""
        headers = await self._get_headers()
        
        params = {"count": 100}
        if since:
            params["startDate"] = since.strftime("%Y-%m-%d")
        
        try:
            response = await self.http_client.get(
                f"{self.BASE_URL}/v1/transactions",
                headers=headers,
                params=params
            )
            response.raise_for_status()
            return response.json().get("transactions", [])
        except httpx.HTTPError as e:
            print(f"토스 API 에러: {e}")
            return []
    
    async def fetch_customers(self) -> List[Dict]:
        """토스는 고객 API 없음 - 거래에서 추출"""
        transactions = await self.fetch_transactions()
        customers = {}
        
        for tx in transactions:
            cust_id = tx.get("orderId", "").split("_")[0]
            if cust_id and cust_id not in customers:
                customers[cust_id] = {
                    "id": cust_id,
                    "total_amount": 0,
                    "transaction_count": 0
                }
            if cust_id:
                customers[cust_id]["total_amount"] += tx.get("totalAmount", 0)
                customers[cust_id]["transaction_count"] += 1
        
        return list(customers.values())
    
    def transform_to_node(self, data: Dict) -> Dict:
        """토스 → AUTUS 노드"""
        return {
            "node_id": data.get("orderId") or data.get("id"),
            "value": data.get("totalAmount") or data.get("total_amount", 0),
            "timestamp": data.get("approvedAt") or datetime.now().isoformat(),
            "source": "toss_pos"
        }


class BaeminPOSClient(BaseSaaSClient):
    """배민포스 API 클라이언트"""
    
    BASE_URL = "https://ceo-api.baemin.com"
    
    async def _get_headers(self) -> Dict:
        return {
            "Authorization": f"Bearer {self.credentials.access_token}",
            "Content-Type": "application/json"
        }
    
    async def fetch_transactions(self, since: Optional[datetime] = None) -> List[Dict]:
        """배민 주문 내역 조회"""
        headers = await self._get_headers()
        
        params = {"limit": 100}
        if since:
            params["startDate"] = since.strftime("%Y-%m-%d")
        
        try:
            response = await self.http_client.get(
                f"{self.BASE_URL}/v1/orders",
                headers=headers,
                params=params
            )
            response.raise_for_status()
            return response.json().get("orders", [])
        except httpx.HTTPError as e:
            print(f"배민 API 에러: {e}")
            return []
    
    async def fetch_customers(self) -> List[Dict]:
        """배민 고객 목록"""
        transactions = await self.fetch_transactions()
        customers = {}
        
        for order in transactions:
            cust_id = order.get("customerId")
            if cust_id and cust_id not in customers:
                customers[cust_id] = {
                    "id": cust_id,
                    "total_amount": 0,
                    "order_count": 0
                }
            if cust_id:
                customers[cust_id]["total_amount"] += order.get("orderAmount", 0)
                customers[cust_id]["order_count"] += 1
        
        return list(customers.values())
    
    def transform_to_node(self, data: Dict) -> Dict:
        """배민 → AUTUS 노드"""
        return {
            "node_id": data.get("orderId") or data.get("id"),
            "value": data.get("orderAmount") or data.get("total_amount", 0),
            "timestamp": data.get("orderTime") or datetime.now().isoformat(),
            "source": "baemin_pos"
        }


class NaverBookingClient(BaseSaaSClient):
    """네이버 예약 API 클라이언트"""
    
    BASE_URL = "https://partner.booking.naver.com/api"
    
    async def _get_headers(self) -> Dict:
        return {
            "X-Naver-Client-Id": self.credentials.api_key,
            "X-Naver-Client-Secret": self.credentials.api_secret,
            "Content-Type": "application/json"
        }
    
    async def fetch_transactions(self, since: Optional[datetime] = None) -> List[Dict]:
        """네이버 예약 내역 조회"""
        headers = await self._get_headers()
        
        try:
            response = await self.http_client.get(
                f"{self.BASE_URL}/v1/bookings",
                headers=headers
            )
            response.raise_for_status()
            return response.json().get("bookings", [])
        except httpx.HTTPError as e:
            print(f"네이버예약 API 에러: {e}")
            return []
    
    async def fetch_customers(self) -> List[Dict]:
        """예약에서 고객 추출"""
        bookings = await self.fetch_transactions()
        customers = {}
        
        for booking in bookings:
            cust_id = booking.get("customerId") or booking.get("bookingId")
            if cust_id and cust_id not in customers:
                customers[cust_id] = {
                    "id": cust_id,
                    "total_amount": 0,
                    "booking_count": 0
                }
            if cust_id:
                customers[cust_id]["total_amount"] += booking.get("totalPrice", 0)
                customers[cust_id]["booking_count"] += 1
        
        return list(customers.values())
    
    def transform_to_node(self, data: Dict) -> Dict:
        """네이버예약 → AUTUS 노드"""
        return {
            "node_id": data.get("customerId") or data.get("id"),
            "value": data.get("totalPrice") or data.get("total_amount", 0),
            "timestamp": data.get("bookingDate") or datetime.now().isoformat(),
            "source": "naver_booking"
        }


class GymSystemClient(BaseSaaSClient):
    """헬스장 관리 시스템 클라이언트"""
    
    BASE_URL = "https://api.gymsystem.co.kr"
    
    async def _get_headers(self) -> Dict:
        return {
            "Authorization": f"Bearer {self.credentials.access_token}",
            "Content-Type": "application/json"
        }
    
    async def fetch_transactions(self, since: Optional[datetime] = None) -> List[Dict]:
        """회원권 결제 내역"""
        headers = await self._get_headers()
        
        try:
            response = await self.http_client.get(
                f"{self.BASE_URL}/v1/payments",
                headers=headers
            )
            response.raise_for_status()
            return response.json().get("payments", [])
        except httpx.HTTPError as e:
            print(f"헬스장 API 에러: {e}")
            return []
    
    async def fetch_customers(self) -> List[Dict]:
        """회원 목록"""
        headers = await self._get_headers()
        
        try:
            response = await self.http_client.get(
                f"{self.BASE_URL}/v1/members",
                headers=headers
            )
            response.raise_for_status()
            return response.json().get("members", [])
        except httpx.HTTPError as e:
            print(f"헬스장 API 에러: {e}")
            return []
    
    def transform_to_node(self, data: Dict) -> Dict:
        """헬스장 → AUTUS 노드"""
        return {
            "node_id": data.get("memberId") or data.get("id"),
            "value": data.get("membershipFee") or data.get("amount", 0),
            "timestamp": data.get("joinDate") or datetime.now().isoformat(),
            "source": "gym_system"
        }


# 클라이언트 팩토리
CLIENT_REGISTRY = {
    "toss_pos": TossPOSClient,
    "baemin_pos": BaeminPOSClient,
    "naver_booking": NaverBookingClient,
    "gym_system": GymSystemClient
}


def get_saas_client(saas_type: str, credentials: SaaSCredentials) -> Optional[BaseSaaSClient]:
    """SaaS 클라이언트 생성"""
    client_class = CLIENT_REGISTRY.get(saas_type)
    if client_class:
        return client_class(credentials)
    return None


async def sync_saas_data(
    saas_type: str,
    credentials: SaaSCredentials,
    since: Optional[datetime] = None
) -> SyncResult:
    """SaaS 데이터 동기화"""
    client = get_saas_client(saas_type, credentials)
    
    if not client:
        return SyncResult(
            success=False,
            errors=[f"Unknown SaaS type: {saas_type}"]
        )
    
    try:
        # 거래 데이터 조회
        transactions = await client.fetch_transactions(since)
        
        # AUTUS 형식으로 변환
        nodes = [client.transform_to_node(tx) for tx in transactions]
        
        await client.close()
        
        return SyncResult(
            success=True,
            records_fetched=len(transactions),
            records_transformed=len(nodes)
        )
    except Exception as e:
        return SyncResult(
            success=False,
            errors=[str(e)]
        )

# backend/parasitic/saas_clients.py
# 실제 SaaS API 클라이언트

import os
import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime
from abc import ABC, abstractmethod

import httpx
from pydantic import BaseModel


class SaaSCredentials(BaseModel):
    """SaaS 인증 정보"""
    api_key: Optional[str] = None
    api_secret: Optional[str] = None
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    merchant_id: Optional[str] = None
    store_url: Optional[str] = None


class SyncResult(BaseModel):
    """동기화 결과"""
    success: bool
    records_fetched: int = 0
    records_transformed: int = 0
    errors: List[str] = []
    timestamp: datetime = datetime.now()


class BaseSaaSClient(ABC):
    """SaaS 클라이언트 베이스"""
    
    def __init__(self, credentials: SaaSCredentials):
        self.credentials = credentials
        self.http_client = httpx.AsyncClient(timeout=30.0)
    
    @abstractmethod
    async def fetch_transactions(self, since: Optional[datetime] = None) -> List[Dict]:
        """거래 데이터 조회"""
        pass
    
    @abstractmethod
    async def fetch_customers(self) -> List[Dict]:
        """고객 데이터 조회"""
        pass
    
    @abstractmethod
    def transform_to_node(self, data: Dict) -> Dict:
        """AUTUS 노드 형식으로 변환"""
        pass
    
    async def close(self):
        await self.http_client.aclose()


class TossPOSClient(BaseSaaSClient):
    """토스 POS API 클라이언트"""
    
    BASE_URL = "https://api.tosspayments.com"
    
    async def _get_headers(self) -> Dict:
        import base64
        auth = base64.b64encode(f"{self.credentials.api_key}:".encode()).decode()
        return {
            "Authorization": f"Basic {auth}",
            "Content-Type": "application/json"
        }
    
    async def fetch_transactions(self, since: Optional[datetime] = None) -> List[Dict]:
        """토스 결제 내역 조회"""
        headers = await self._get_headers()
        
        params = {"count": 100}
        if since:
            params["startDate"] = since.strftime("%Y-%m-%d")
        
        try:
            response = await self.http_client.get(
                f"{self.BASE_URL}/v1/transactions",
                headers=headers,
                params=params
            )
            response.raise_for_status()
            return response.json().get("transactions", [])
        except httpx.HTTPError as e:
            print(f"토스 API 에러: {e}")
            return []
    
    async def fetch_customers(self) -> List[Dict]:
        """토스는 고객 API 없음 - 거래에서 추출"""
        transactions = await self.fetch_transactions()
        customers = {}
        
        for tx in transactions:
            cust_id = tx.get("orderId", "").split("_")[0]
            if cust_id and cust_id not in customers:
                customers[cust_id] = {
                    "id": cust_id,
                    "total_amount": 0,
                    "transaction_count": 0
                }
            if cust_id:
                customers[cust_id]["total_amount"] += tx.get("totalAmount", 0)
                customers[cust_id]["transaction_count"] += 1
        
        return list(customers.values())
    
    def transform_to_node(self, data: Dict) -> Dict:
        """토스 → AUTUS 노드"""
        return {
            "node_id": data.get("orderId") or data.get("id"),
            "value": data.get("totalAmount") or data.get("total_amount", 0),
            "timestamp": data.get("approvedAt") or datetime.now().isoformat(),
            "source": "toss_pos"
        }


class BaeminPOSClient(BaseSaaSClient):
    """배민포스 API 클라이언트"""
    
    BASE_URL = "https://ceo-api.baemin.com"
    
    async def _get_headers(self) -> Dict:
        return {
            "Authorization": f"Bearer {self.credentials.access_token}",
            "Content-Type": "application/json"
        }
    
    async def fetch_transactions(self, since: Optional[datetime] = None) -> List[Dict]:
        """배민 주문 내역 조회"""
        headers = await self._get_headers()
        
        params = {"limit": 100}
        if since:
            params["startDate"] = since.strftime("%Y-%m-%d")
        
        try:
            response = await self.http_client.get(
                f"{self.BASE_URL}/v1/orders",
                headers=headers,
                params=params
            )
            response.raise_for_status()
            return response.json().get("orders", [])
        except httpx.HTTPError as e:
            print(f"배민 API 에러: {e}")
            return []
    
    async def fetch_customers(self) -> List[Dict]:
        """배민 고객 목록"""
        transactions = await self.fetch_transactions()
        customers = {}
        
        for order in transactions:
            cust_id = order.get("customerId")
            if cust_id and cust_id not in customers:
                customers[cust_id] = {
                    "id": cust_id,
                    "total_amount": 0,
                    "order_count": 0
                }
            if cust_id:
                customers[cust_id]["total_amount"] += order.get("orderAmount", 0)
                customers[cust_id]["order_count"] += 1
        
        return list(customers.values())
    
    def transform_to_node(self, data: Dict) -> Dict:
        """배민 → AUTUS 노드"""
        return {
            "node_id": data.get("orderId") or data.get("id"),
            "value": data.get("orderAmount") or data.get("total_amount", 0),
            "timestamp": data.get("orderTime") or datetime.now().isoformat(),
            "source": "baemin_pos"
        }


class NaverBookingClient(BaseSaaSClient):
    """네이버 예약 API 클라이언트"""
    
    BASE_URL = "https://partner.booking.naver.com/api"
    
    async def _get_headers(self) -> Dict:
        return {
            "X-Naver-Client-Id": self.credentials.api_key,
            "X-Naver-Client-Secret": self.credentials.api_secret,
            "Content-Type": "application/json"
        }
    
    async def fetch_transactions(self, since: Optional[datetime] = None) -> List[Dict]:
        """네이버 예약 내역 조회"""
        headers = await self._get_headers()
        
        try:
            response = await self.http_client.get(
                f"{self.BASE_URL}/v1/bookings",
                headers=headers
            )
            response.raise_for_status()
            return response.json().get("bookings", [])
        except httpx.HTTPError as e:
            print(f"네이버예약 API 에러: {e}")
            return []
    
    async def fetch_customers(self) -> List[Dict]:
        """예약에서 고객 추출"""
        bookings = await self.fetch_transactions()
        customers = {}
        
        for booking in bookings:
            cust_id = booking.get("customerId") or booking.get("bookingId")
            if cust_id and cust_id not in customers:
                customers[cust_id] = {
                    "id": cust_id,
                    "total_amount": 0,
                    "booking_count": 0
                }
            if cust_id:
                customers[cust_id]["total_amount"] += booking.get("totalPrice", 0)
                customers[cust_id]["booking_count"] += 1
        
        return list(customers.values())
    
    def transform_to_node(self, data: Dict) -> Dict:
        """네이버예약 → AUTUS 노드"""
        return {
            "node_id": data.get("customerId") or data.get("id"),
            "value": data.get("totalPrice") or data.get("total_amount", 0),
            "timestamp": data.get("bookingDate") or datetime.now().isoformat(),
            "source": "naver_booking"
        }


class GymSystemClient(BaseSaaSClient):
    """헬스장 관리 시스템 클라이언트"""
    
    BASE_URL = "https://api.gymsystem.co.kr"
    
    async def _get_headers(self) -> Dict:
        return {
            "Authorization": f"Bearer {self.credentials.access_token}",
            "Content-Type": "application/json"
        }
    
    async def fetch_transactions(self, since: Optional[datetime] = None) -> List[Dict]:
        """회원권 결제 내역"""
        headers = await self._get_headers()
        
        try:
            response = await self.http_client.get(
                f"{self.BASE_URL}/v1/payments",
                headers=headers
            )
            response.raise_for_status()
            return response.json().get("payments", [])
        except httpx.HTTPError as e:
            print(f"헬스장 API 에러: {e}")
            return []
    
    async def fetch_customers(self) -> List[Dict]:
        """회원 목록"""
        headers = await self._get_headers()
        
        try:
            response = await self.http_client.get(
                f"{self.BASE_URL}/v1/members",
                headers=headers
            )
            response.raise_for_status()
            return response.json().get("members", [])
        except httpx.HTTPError as e:
            print(f"헬스장 API 에러: {e}")
            return []
    
    def transform_to_node(self, data: Dict) -> Dict:
        """헬스장 → AUTUS 노드"""
        return {
            "node_id": data.get("memberId") or data.get("id"),
            "value": data.get("membershipFee") or data.get("amount", 0),
            "timestamp": data.get("joinDate") or datetime.now().isoformat(),
            "source": "gym_system"
        }


# 클라이언트 팩토리
CLIENT_REGISTRY = {
    "toss_pos": TossPOSClient,
    "baemin_pos": BaeminPOSClient,
    "naver_booking": NaverBookingClient,
    "gym_system": GymSystemClient
}


def get_saas_client(saas_type: str, credentials: SaaSCredentials) -> Optional[BaseSaaSClient]:
    """SaaS 클라이언트 생성"""
    client_class = CLIENT_REGISTRY.get(saas_type)
    if client_class:
        return client_class(credentials)
    return None


async def sync_saas_data(
    saas_type: str,
    credentials: SaaSCredentials,
    since: Optional[datetime] = None
) -> SyncResult:
    """SaaS 데이터 동기화"""
    client = get_saas_client(saas_type, credentials)
    
    if not client:
        return SyncResult(
            success=False,
            errors=[f"Unknown SaaS type: {saas_type}"]
        )
    
    try:
        # 거래 데이터 조회
        transactions = await client.fetch_transactions(since)
        
        # AUTUS 형식으로 변환
        nodes = [client.transform_to_node(tx) for tx in transactions]
        
        await client.close()
        
        return SyncResult(
            success=True,
            records_fetched=len(transactions),
            records_transformed=len(nodes)
        )
    except Exception as e:
        return SyncResult(
            success=False,
            errors=[str(e)]
        )



