"""
AUTUS Physics Map Engine v2
===========================

v1.0 정본 준수:
- Local-Only (No external calls)
- Semantic Neutrality (σ = volatility, not "lies")
- No judgment, only physics

Features:
- σ (Sigma) zones: volatility measurement
- Gravity Wells: Entity mass/influence
- L0-L1-L2 depth layers
- Energy flow computation
- n^n scaling simulation
"""

from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional
from enum import Enum
import math
import hashlib
import json


# =============================================================================
# CONSTANTS (LOCKED)
# =============================================================================

SIGMA_LOW = 0.3       # Low volatility threshold
SIGMA_HIGH = 0.6      # High volatility threshold
GRAVITY_CONSTANT = 1.0  # For gravity well calculation


class Layer(Enum):
    """Entity proximity layers."""
    L0_SELF = 0
    L1_DIRECT = 1
    L2_INDIRECT = 2


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class Entity:
    """
    Person entity in Physics Map.
    
    All values are physical measurements, not judgments.
    """
    id: str
    layer: Layer
    x: float  # Position [0, 1]
    y: float  # Position [0, 1]
    
    # Physical properties
    sigma: float = 0.3    # Volatility (NOT "lies")
    energy: float = 50.0  # Energy level
    mass: float = 0.5     # Influence mass
    cu: float = 0.0       # Accumulated cost
    
    # 6D state (hidden)
    state: Tuple[float, ...] = field(default_factory=lambda: (0.5,) * 6)
    
    def __post_init__(self):
        # Clamp values
        self.sigma = max(0.0, min(1.0, self.sigma))
        self.energy = max(0.0, self.energy)
        self.mass = max(0.0, min(1.0, self.mass))
    
    def get_sigma_level(self) -> str:
        """Get sigma classification (for color mapping only)."""
        if self.sigma < SIGMA_LOW:
            return 'low'
        elif self.sigma < SIGMA_HIGH:
            return 'mid'
        else:
            return 'high'
    
    def hash(self) -> str:
        """Deterministic hash for NFT chain."""
        data = {
            'id': self.id,
            'sigma': round(self.sigma, 4),
            'energy': round(self.energy, 4),
            'mass': round(self.mass, 4),
            'cu': round(self.cu, 4),
        }
        return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()[:16]


@dataclass
class Connection:
    """
    CU flow connection between entities.
    """
    from_id: str
    to_id: str
    cu_flow: float  # Cost units per time
    
    def __post_init__(self):
        self.cu_flow = max(0.0, self.cu_flow)


@dataclass
class SigmaZone:
    """
    High volatility zone in the map.
    
    This represents areas of high σ (volatility).
    NOT "lies cloud" - just physics measurement.
    """
    x: float
    y: float
    radius: float
    sigma: float
    
    def contains(self, px: float, py: float) -> bool:
        """Check if point is within zone."""
        dx = px - self.x
        dy = py - self.y
        return (dx * dx + dy * dy) <= (self.radius * self.radius)
    
    def get_influence(self, px: float, py: float) -> float:
        """Get sigma influence at point (0-1)."""
        dx = px - self.x
        dy = py - self.y
        dist = math.sqrt(dx * dx + dy * dy)
        if dist >= self.radius:
            return 0.0
        return self.sigma * (1 - dist / self.radius)


# =============================================================================
# PHYSICS MAP
# =============================================================================

class PhysicsMap:
    """
    AUTUS Physics Map.
    
    Local-only computation of entity relationships and CU flow.
    """
    
    def __init__(self):
        self.entities: Dict[str, Entity] = {}
        self.connections: List[Connection] = []
        self.sigma_zones: List[SigmaZone] = []
        self._self_id: Optional[str] = None
    
    def add_self(self, energy: float = 100.0) -> Entity:
        """Add the SELF entity (L0)."""
        entity = Entity(
            id='self',
            layer=Layer.L0_SELF,
            x=0.5,
            y=0.5,
            sigma=0.1,  # Low volatility for self
            energy=energy,
            mass=1.0,   # Reference mass
        )
        self.entities['self'] = entity
        self._self_id = 'self'
        return entity
    
    def add_entity(
        self,
        id: str,
        layer: Layer,
        x: float,
        y: float,
        sigma: float = 0.3,
        energy: float = 50.0,
        mass: float = 0.5,
    ) -> Entity:
        """Add an entity to the map."""
        entity = Entity(
            id=id,
            layer=layer,
            x=x,
            y=y,
            sigma=sigma,
            energy=energy,
            mass=mass,
        )
        self.entities[id] = entity
        return entity
    
    def add_connection(self, from_id: str, to_id: str, cu_flow: float) -> Connection:
        """Add a CU flow connection."""
        conn = Connection(from_id, to_id, cu_flow)
        self.connections.append(conn)
        return conn
    
    def add_sigma_zone(self, x: float, y: float, radius: float, sigma: float) -> SigmaZone:
        """Add a high-σ zone."""
        zone = SigmaZone(x, y, radius, sigma)
        self.sigma_zones.append(zone)
        return zone
    
    # =========================================================================
    # PHYSICS CALCULATIONS
    # =========================================================================
    
    def compute_gravity_well(self, entity: Entity) -> float:
        """
        Compute gravity well strength for entity.
        
        Gravity = mass × energy
        """
        return GRAVITY_CONSTANT * entity.mass * (entity.energy / 100.0)
    
    def compute_sigma_at_point(self, x: float, y: float) -> float:
        """
        Compute total σ influence at a point.
        
        Sum of all zone influences.
        """
        total = 0.0
        for zone in self.sigma_zones:
            total += zone.get_influence(x, y)
        return min(1.0, total)
    
    def compute_effective_energy(self, entity: Entity) -> float:
        """
        Compute effective energy considering σ at entity position.
        
        E_eff = E × (1 - σ_local)
        """
        sigma_local = self.compute_sigma_at_point(entity.x, entity.y)
        combined_sigma = max(entity.sigma, sigma_local)
        return entity.energy * (1 - combined_sigma)
    
    def compute_cu_rate(self) -> float:
        """Compute total CU flow rate."""
        return sum(c.cu_flow for c in self.connections)
    
    def compute_total_energy(self) -> float:
        """Compute total energy in the map."""
        return sum(e.energy for e in self.entities.values())
    
    def compute_average_sigma(self) -> float:
        """Compute average σ across all entities."""
        if not self.entities:
            return 0.0
        return sum(e.sigma for e in self.entities.values()) / len(self.entities)
    
    def compute_entropy(self) -> float:
        """
        Compute system entropy.
        
        H = Σ (σᵢ × log(1 + Eᵢ))
        """
        H = 0.0
        for entity in self.entities.values():
            H += entity.sigma * math.log(1 + entity.energy)
        return H
    
    # =========================================================================
    # LAYER OPERATIONS
    # =========================================================================
    
    def get_entities_by_layer(self, layer: Layer) -> List[Entity]:
        """Get all entities at a specific layer."""
        return [e for e in self.entities.values() if e.layer == layer]
    
    def get_visible_entities(self, active_layer: Layer) -> List[Entity]:
        """Get entities visible at the active layer depth."""
        max_layer = active_layer.value + 1
        return [e for e in self.entities.values() if e.layer.value <= max_layer]
    
    def get_connections_for_layer(self, active_layer: Layer) -> List[Connection]:
        """Get connections visible at the active layer depth."""
        max_layer = active_layer.value + 1
        visible_ids = {e.id for e in self.get_visible_entities(active_layer)}
        return [c for c in self.connections 
                if c.from_id in visible_ids and c.to_id in visible_ids]
    
    # =========================================================================
    # SERIALIZATION
    # =========================================================================
    
    def to_dict(self) -> dict:
        """Export map state (for local storage)."""
        return {
            'entities': {
                id: {
                    'id': e.id,
                    'layer': e.layer.value,
                    'x': e.x,
                    'y': e.y,
                    'sigma': e.sigma,
                    'energy': e.energy,
                    'mass': e.mass,
                    'cu': e.cu,
                }
                for id, e in self.entities.items()
            },
            'connections': [
                {'from': c.from_id, 'to': c.to_id, 'cu_flow': c.cu_flow}
                for c in self.connections
            ],
            'sigma_zones': [
                {'x': z.x, 'y': z.y, 'radius': z.radius, 'sigma': z.sigma}
                for z in self.sigma_zones
            ],
        }
    
    def get_stats(self) -> dict:
        """Get map statistics."""
        return {
            'entity_count': len(self.entities),
            'connection_count': len(self.connections),
            'sigma_zone_count': len(self.sigma_zones),
            'total_energy': self.compute_total_energy(),
            'average_sigma': self.compute_average_sigma(),
            'cu_rate': self.compute_cu_rate(),
            'entropy': self.compute_entropy(),
        }


# =============================================================================
# n^n SCALING SIMULATOR
# =============================================================================

class NNScalingSimulator:
    """
    n^n Scaling Simulator.
    
    Demonstrates combinatorial state explosion in entity networks.
    All computation is local.
    
    Formula: V = n^n × E₀ × (1 - σ) × α
    """
    
    def __init__(
        self,
        base_energy: float = 1.0,
        sigma: float = 0.3,
        alpha: float = 0.5,
    ):
        self.base_energy = base_energy
        self.sigma = sigma  # Volatility
        self.alpha = alpha  # Interaction rate
    
    def compute_n_to_n(self, n: int) -> float:
        """
        Compute n^n with overflow protection.
        """
        if n <= 0:
            return 0
        if n > 170:
            # Beyond float range, use infinity
            return float('inf')
        if n > 20:
            # Use logarithm for large n
            return math.exp(n * math.log(n))
        return math.pow(n, n)
    
    def compute_value(self, n: int) -> float:
        """
        Compute total value output.
        
        V = n^n × E₀ × (1 - σ) × α
        """
        n_to_n = self.compute_n_to_n(n)
        return n_to_n * self.base_energy * (1 - self.sigma) * self.alpha
    
    def compute_cu(self, n: int) -> float:
        """
        Compute CU accumulation.
        
        CU = n × (n-1) / 2 × α (pairwise interactions)
        """
        return (n * (n - 1) / 2) * self.alpha
    
    def compute_entropy(self, n: int) -> float:
        """
        Compute system entropy.
        
        H = n × log(n) × σ
        """
        if n <= 1:
            return 0
        return n * math.log(n) * self.sigma
    
    def simulate(self, n: int) -> dict:
        """
        Run full simulation for n entities.
        """
        n_to_n = self.compute_n_to_n(n)
        value = self.compute_value(n)
        cu = self.compute_cu(n)
        entropy = self.compute_entropy(n)
        
        # Determine status (physics-based, not judgment)
        if value > 1e12 or math.isinf(value):
            status = 'overflow'
        elif value > 1e6:
            status = 'high'
        else:
            status = 'stable'
        
        return {
            'n': n,
            'n_to_n': n_to_n,
            'value': value,
            'cu': cu,
            'entropy': entropy,
            'status': status,
            'parameters': {
                'base_energy': self.base_energy,
                'sigma': self.sigma,
                'alpha': self.alpha,
            }
        }
    
    def simulate_range(self, n_values: List[int]) -> List[dict]:
        """Simulate for multiple n values."""
        return [self.simulate(n) for n in n_values]


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def format_large_number(num: float) -> str:
    """Format large numbers for display."""
    if math.isinf(num):
        return '∞'
    if num >= 1e15:
        return f'{num:.2e}'
    if num >= 1e12:
        return f'{num/1e12:.2f}T'
    if num >= 1e9:
        return f'{num/1e9:.2f}B'
    if num >= 1e6:
        return f'{num/1e6:.2f}M'
    if num >= 1e3:
        return f'{num/1e3:.2f}K'
    return f'{num:.2f}'


# =============================================================================
# DEMO
# =============================================================================

if __name__ == '__main__':
    print("=" * 60)
    print("AUTUS Physics Map v2 - Demo")
    print("=" * 60)
    
    # Create physics map
    pmap = PhysicsMap()
    
    # Add SELF
    pmap.add_self(energy=100)
    
    # Add L1 entities
    import random
    for i in range(5):
        angle = (i / 5) * math.pi * 2
        r = 0.2
        pmap.add_entity(
            id=f'l1_{i}',
            layer=Layer.L1_DIRECT,
            x=0.5 + math.cos(angle) * r,
            y=0.5 + math.sin(angle) * r,
            sigma=0.2 + random.random() * 0.3,
            energy=30 + random.random() * 50,
            mass=0.3 + random.random() * 0.4,
        )
        pmap.add_connection('self', f'l1_{i}', 1 + random.random() * 3)
    
    # Add σ zones
    pmap.add_sigma_zone(0.3, 0.3, 0.1, 0.7)
    pmap.add_sigma_zone(0.7, 0.6, 0.12, 0.8)
    
    # Print stats
    print("\nPhysics Map Stats:")
    stats = pmap.get_stats()
    for key, value in stats.items():
        if isinstance(value, float):
            print(f"  {key}: {value:.4f}")
        else:
            print(f"  {key}: {value}")
    
    # n^n Scaling
    print("\n" + "=" * 60)
    print("n^n Scaling Simulation")
    print("=" * 60)
    
    simulator = NNScalingSimulator(
        base_energy=1.0,
        sigma=0.3,
        alpha=0.5,
    )
    
    print("\n  n    |    n^n      |    Value    |    CU    | Status")
    print("-" * 60)
    
    for n in [2, 5, 10, 20, 50, 100]:
        result = simulator.simulate(n)
        print(f"  {n:3d}  | {format_large_number(result['n_to_n']):>10s} | "
              f"{format_large_number(result['value']):>10s} | "
              f"{result['cu']:>7.1f} | {result['status']}")
    
    print("\n✓ All computations local. No external calls.")
