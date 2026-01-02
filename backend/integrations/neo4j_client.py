# backend/integrations/neo4j_client.py
# Neo4j 그래프 DB 연동

from typing import Dict, List, Optional
from datetime import datetime
import os

class Neo4jClient:
    """
    Neo4j 클라이언트
    
    노드 (고객) + 모션 (돈 흐름) 관리
    """
    
    def __init__(self):
        self.uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
        self.user = os.getenv("NEO4J_USER", "neo4j")
        self.password = os.getenv("NEO4J_PASSWORD", "password")
        self._driver = None
    
    async def connect(self):
        """연결"""
        try:
            from neo4j import AsyncGraphDatabase
            self._driver = AsyncGraphDatabase.driver(
                self.uri, 
                auth=(self.user, self.password)
            )
        except ImportError:
            # neo4j 패키지 없으면 Mock 모드
            self._driver = None
            print("⚠️ neo4j package not installed - Mock mode")
    
    async def close(self):
        """연결 종료"""
        if self._driver:
            await self._driver.close()
    
    async def upsert_node(
        self,
        external_id: str,
        source: str = "unknown",
        initial_value: float = 0
    ) -> Dict:
        """
        노드 생성/업데이트 (MERGE)
        
        Zero Meaning: external_id만 저장 (이름/이메일 없음)
        """
        if not self._driver:
            # Mock 응답
            return {
                "id": f"mock_{external_id}",
                "external_id": external_id,
                "source": source,
                "value": initial_value,
                "created": True
            }
        
        async with self._driver.session() as session:
            result = await session.run("""
                MERGE (n:Node {external_id: $external_id})
                ON CREATE SET 
                    n.source = $source,
                    n.value = $initial_value,
                    n.created_at = datetime()
                ON MATCH SET
                    n.updated_at = datetime()
                RETURN n.external_id as external_id, 
                       n.source as source, 
                       n.value as value,
                       n.created_at as created_at
            """, 
                external_id=external_id,
                source=source,
                initial_value=initial_value
            )
            
            record = await result.single()
            return dict(record) if record else None
    
    async def create_motion(
        self,
        source_id: str,
        target_id: str,
        amount: float,
        direction: str = "inflow"
    ) -> Dict:
        """
        돈 모션 생성 (FLOW 관계)
        
        direction:
        - inflow: 고객 → owner
        - outflow: owner → 고객
        """
        if not self._driver:
            # Mock 응답
            return {
                "id": f"motion_{datetime.now().timestamp()}",
                "source": source_id,
                "target": target_id,
                "amount": amount,
                "direction": direction,
                "created": True
            }
        
        async with self._driver.session() as session:
            # 노드가 없으면 생성
            await session.run("""
                MERGE (a:Node {external_id: $source_id})
                MERGE (b:Node {external_id: $target_id})
            """, source_id=source_id, target_id=target_id)
            
            # 모션 (관계) 생성
            result = await session.run("""
                MATCH (a:Node {external_id: $source_id})
                MATCH (b:Node {external_id: $target_id})
                CREATE (a)-[r:FLOW {
                    amount: $amount,
                    direction: $direction,
                    created_at: datetime()
                }]->(b)
                RETURN id(r) as id, r.amount as amount, r.direction as direction
            """,
                source_id=source_id,
                target_id=target_id,
                amount=amount,
                direction=direction
            )
            
            record = await result.single()
            
            # 가치 업데이트
            await self._update_node_value(session, source_id if direction == "outflow" else target_id)
            
            return dict(record) if record else None
    
    async def _update_node_value(self, session, node_id: str):
        """노드 가치 재계산 (V = M - T + S)"""
        await session.run("""
            MATCH (n:Node {external_id: $node_id})
            OPTIONAL MATCH (n)<-[inflow:FLOW {direction: 'inflow'}]-()
            OPTIONAL MATCH (n)-[outflow:FLOW {direction: 'outflow'}]->()
            WITH n,
                 coalesce(sum(inflow.amount), 0) as total_inflow,
                 coalesce(sum(outflow.amount), 0) as total_outflow
            SET n.value = total_inflow - total_outflow
            RETURN n.value
        """, node_id=node_id)
    
    async def get_all_nodes(self, limit: int = 1000) -> List[Dict]:
        """전체 노드 조회 (Physics Map용)"""
        if not self._driver:
            return []
        
        async with self._driver.session() as session:
            result = await session.run("""
                MATCH (n:Node)
                RETURN n.external_id as id, n.value as value, n.source as source
                LIMIT $limit
            """, limit=limit)
            
            return [dict(record) async for record in result]
    
    async def get_all_motions(self, limit: int = 5000) -> List[Dict]:
        """전체 모션 조회 (Physics Map용)"""
        if not self._driver:
            return []
        
        async with self._driver.session() as session:
            result = await session.run("""
                MATCH (a:Node)-[r:FLOW]->(b:Node)
                RETURN a.external_id as source, 
                       b.external_id as target,
                       r.amount as amount,
                       r.direction as direction
                LIMIT $limit
            """, limit=limit)
            
            return [dict(record) async for record in result]
    
    async def calculate_synergy(self, node_id: str, rate: float = 0.1) -> float:
        """
        시너지 계산
        
        S = Σ(connected_value × rate^depth)
        """
        if not self._driver:
            return 0.0
        
        async with self._driver.session() as session:
            result = await session.run("""
                MATCH (n:Node {external_id: $node_id})-[:FLOW*1..3]-(connected:Node)
                WITH connected, 
                     length(shortestPath((n)-[:FLOW*]-(connected))) as depth
                RETURN sum(connected.value * power($rate, depth)) as synergy
            """, node_id=node_id, rate=rate)
            
            record = await result.single()
            return record["synergy"] if record else 0.0

# backend/integrations/neo4j_client.py
# Neo4j 그래프 DB 연동

from typing import Dict, List, Optional
from datetime import datetime
import os

class Neo4jClient:
    """
    Neo4j 클라이언트
    
    노드 (고객) + 모션 (돈 흐름) 관리
    """
    
    def __init__(self):
        self.uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
        self.user = os.getenv("NEO4J_USER", "neo4j")
        self.password = os.getenv("NEO4J_PASSWORD", "password")
        self._driver = None
    
    async def connect(self):
        """연결"""
        try:
            from neo4j import AsyncGraphDatabase
            self._driver = AsyncGraphDatabase.driver(
                self.uri, 
                auth=(self.user, self.password)
            )
        except ImportError:
            # neo4j 패키지 없으면 Mock 모드
            self._driver = None
            print("⚠️ neo4j package not installed - Mock mode")
    
    async def close(self):
        """연결 종료"""
        if self._driver:
            await self._driver.close()
    
    async def upsert_node(
        self,
        external_id: str,
        source: str = "unknown",
        initial_value: float = 0
    ) -> Dict:
        """
        노드 생성/업데이트 (MERGE)
        
        Zero Meaning: external_id만 저장 (이름/이메일 없음)
        """
        if not self._driver:
            # Mock 응답
            return {
                "id": f"mock_{external_id}",
                "external_id": external_id,
                "source": source,
                "value": initial_value,
                "created": True
            }
        
        async with self._driver.session() as session:
            result = await session.run("""
                MERGE (n:Node {external_id: $external_id})
                ON CREATE SET 
                    n.source = $source,
                    n.value = $initial_value,
                    n.created_at = datetime()
                ON MATCH SET
                    n.updated_at = datetime()
                RETURN n.external_id as external_id, 
                       n.source as source, 
                       n.value as value,
                       n.created_at as created_at
            """, 
                external_id=external_id,
                source=source,
                initial_value=initial_value
            )
            
            record = await result.single()
            return dict(record) if record else None
    
    async def create_motion(
        self,
        source_id: str,
        target_id: str,
        amount: float,
        direction: str = "inflow"
    ) -> Dict:
        """
        돈 모션 생성 (FLOW 관계)
        
        direction:
        - inflow: 고객 → owner
        - outflow: owner → 고객
        """
        if not self._driver:
            # Mock 응답
            return {
                "id": f"motion_{datetime.now().timestamp()}",
                "source": source_id,
                "target": target_id,
                "amount": amount,
                "direction": direction,
                "created": True
            }
        
        async with self._driver.session() as session:
            # 노드가 없으면 생성
            await session.run("""
                MERGE (a:Node {external_id: $source_id})
                MERGE (b:Node {external_id: $target_id})
            """, source_id=source_id, target_id=target_id)
            
            # 모션 (관계) 생성
            result = await session.run("""
                MATCH (a:Node {external_id: $source_id})
                MATCH (b:Node {external_id: $target_id})
                CREATE (a)-[r:FLOW {
                    amount: $amount,
                    direction: $direction,
                    created_at: datetime()
                }]->(b)
                RETURN id(r) as id, r.amount as amount, r.direction as direction
            """,
                source_id=source_id,
                target_id=target_id,
                amount=amount,
                direction=direction
            )
            
            record = await result.single()
            
            # 가치 업데이트
            await self._update_node_value(session, source_id if direction == "outflow" else target_id)
            
            return dict(record) if record else None
    
    async def _update_node_value(self, session, node_id: str):
        """노드 가치 재계산 (V = M - T + S)"""
        await session.run("""
            MATCH (n:Node {external_id: $node_id})
            OPTIONAL MATCH (n)<-[inflow:FLOW {direction: 'inflow'}]-()
            OPTIONAL MATCH (n)-[outflow:FLOW {direction: 'outflow'}]->()
            WITH n,
                 coalesce(sum(inflow.amount), 0) as total_inflow,
                 coalesce(sum(outflow.amount), 0) as total_outflow
            SET n.value = total_inflow - total_outflow
            RETURN n.value
        """, node_id=node_id)
    
    async def get_all_nodes(self, limit: int = 1000) -> List[Dict]:
        """전체 노드 조회 (Physics Map용)"""
        if not self._driver:
            return []
        
        async with self._driver.session() as session:
            result = await session.run("""
                MATCH (n:Node)
                RETURN n.external_id as id, n.value as value, n.source as source
                LIMIT $limit
            """, limit=limit)
            
            return [dict(record) async for record in result]
    
    async def get_all_motions(self, limit: int = 5000) -> List[Dict]:
        """전체 모션 조회 (Physics Map용)"""
        if not self._driver:
            return []
        
        async with self._driver.session() as session:
            result = await session.run("""
                MATCH (a:Node)-[r:FLOW]->(b:Node)
                RETURN a.external_id as source, 
                       b.external_id as target,
                       r.amount as amount,
                       r.direction as direction
                LIMIT $limit
            """, limit=limit)
            
            return [dict(record) async for record in result]
    
    async def calculate_synergy(self, node_id: str, rate: float = 0.1) -> float:
        """
        시너지 계산
        
        S = Σ(connected_value × rate^depth)
        """
        if not self._driver:
            return 0.0
        
        async with self._driver.session() as session:
            result = await session.run("""
                MATCH (n:Node {external_id: $node_id})-[:FLOW*1..3]-(connected:Node)
                WITH connected, 
                     length(shortestPath((n)-[:FLOW*]-(connected))) as depth
                RETURN sum(connected.value * power($rate, depth)) as synergy
            """, node_id=node_id, rate=rate)
            
            record = await result.single()
            return record["synergy"] if record else 0.0



