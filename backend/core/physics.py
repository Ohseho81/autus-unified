"""
AUTUS Physics Core
==================

Deterministic state update system.
Same physics for all persons.
θ (theta) is private and non-semantic.

IMPORTANT:
- Do not add randomness
- Do not expose θ
- Do not interpret state values
- State is measurement, not judgment

State Model:
- Core (6D): [stability, pressure, drag, momentum, volatility, recovery]
- Display (3D): [E, F, R] (projection of 6D)
"""

from dataclasses import dataclass
from typing import Tuple
import hashlib
import json


@dataclass
class CoreState:
    """
    Hidden 6D state vector.
    All values normalized to [0, 1].
    
    DO NOT expose individual components to UI.
    Only expose 3D projection (E, F, R).
    """
    stability: float    # Structural stability
    pressure: float     # External/internal pressure
    drag: float         # Resistance/friction
    momentum: float     # Inertia
    volatility: float   # Variance
    recovery: float     # Recovery capacity
    
    def __post_init__(self):
        # Clamp all values to [0, 1]
        self.stability = max(0.0, min(1.0, self.stability))
        self.pressure = max(0.0, min(1.0, self.pressure))
        self.drag = max(0.0, min(1.0, self.drag))
        self.momentum = max(0.0, min(1.0, self.momentum))
        self.volatility = max(0.0, min(1.0, self.volatility))
        self.recovery = max(0.0, min(1.0, self.recovery))
    
    def to_vector(self) -> Tuple[float, ...]:
        return (
            self.stability,
            self.pressure,
            self.drag,
            self.momentum,
            self.volatility,
            self.recovery
        )
    
    def hash(self) -> str:
        """Deterministic hash for NFT chain."""
        data = json.dumps(self.to_vector(), sort_keys=True)
        return hashlib.sha256(data.encode()).hexdigest()[:16]


@dataclass
class DisplayState:
    """
    UI-visible 3D projection.
    Derived from CoreState, not stored independently.
    
    E = Energy (stability, recovery)
    F = Flow (momentum, drag)
    R = Risk (pressure, volatility)
    """
    E: float  # Energy
    F: float  # Flow
    R: float  # Risk


def project_to_display(core: CoreState) -> DisplayState:
    """
    Project 6D core state to 3D display state.
    
    This is the ONLY way to expose state to UI.
    Core state components are never shown directly.
    """
    E = 0.6 * core.stability + 0.4 * core.recovery
    F = 0.7 * core.momentum - 0.3 * core.drag
    R = 0.5 * core.pressure + 0.5 * core.volatility
    
    # Clamp to [0, 1]
    E = max(0.0, min(1.0, E))
    F = max(0.0, min(1.0, F))
    R = max(0.0, min(1.0, R))
    
    return DisplayState(E=E, F=F, R=R)


class PhysicsEngine:
    """
    Deterministic physics engine.
    
    RULES:
    - Same input → same output (ALWAYS)
    - No randomness
    - θ parameters are per-person and hidden
    - No interpretation of "good" or "bad"
    """
    
    def __init__(self, theta: dict = None):
        """
        Initialize with optional theta parameters.
        
        theta is PRIVATE and NEVER exposed to:
        - UI
        - Logs
        - External systems
        """
        self._theta = theta or self._default_theta()
    
    def _default_theta(self) -> dict:
        """Default theta (hidden parameters)."""
        return {
            'decay_rate': 0.02,
            'pressure_sensitivity': 0.15,
            'momentum_inertia': 0.85,
            'recovery_rate': 0.05,
        }
    
    def update(self, state: CoreState, action: str, dt: float = 1.0) -> CoreState:
        """
        Deterministic state update.
        
        Args:
            state: Current 6D state
            action: One of ['HOLD', 'PUSH', 'DRIFT']
            dt: Time delta
        
        Returns:
            New CoreState (deterministic)
        
        NOTE: This function MUST be deterministic.
        Same (state, action, dt) → same result.
        """
        s = state.stability
        p = state.pressure
        d = state.drag
        m = state.momentum
        v = state.volatility
        r = state.recovery
        
        θ = self._theta
        
        if action == 'HOLD':
            # Maintain current trajectory
            s += θ['recovery_rate'] * dt * (1 - s)
            p *= (1 - θ['decay_rate'] * dt)
            m *= θ['momentum_inertia']
            
        elif action == 'PUSH':
            # Increase momentum, accept risk
            m += 0.1 * dt * (1 - m)
            p += θ['pressure_sensitivity'] * dt
            v += 0.05 * dt
            d *= 0.95
            
        elif action == 'DRIFT':
            # Reduce drag, accept volatility
            d *= (1 - 0.1 * dt)
            s += θ['recovery_rate'] * dt * 0.5
            v += 0.02 * dt
        
        return CoreState(
            stability=s,
            pressure=p,
            drag=d,
            momentum=m,
            volatility=v,
            recovery=r
        )
    
    def compute_delta(self, s1: CoreState, s2: CoreState) -> Tuple[float, ...]:
        """
        Compute ΔS between two states.
        
        Returns delta vector (6D).
        This is physics measurement, not judgment.
        """
        v1 = s1.to_vector()
        v2 = s2.to_vector()
        return tuple(b - a for a, b in zip(v1, v2))
    
    def compute_delta_magnitude(self, s1: CoreState, s2: CoreState) -> float:
        """
        Compute |ΔS| (Euclidean magnitude).
        
        Used for ΔS/Δt (state divergence rate).
        This replaces "Loss Velocity" terminology.
        """
        delta = self.compute_delta(s1, s2)
        return sum(d ** 2 for d in delta) ** 0.5


# Determinism verification
def verify_determinism():
    """
    Verify that physics engine is deterministic.
    This should be run as part of test suite.
    """
    engine = PhysicsEngine()
    state = CoreState(0.5, 0.3, 0.2, 0.6, 0.1, 0.7)
    
    result1 = engine.update(state, 'PUSH', 1.0)
    result2 = engine.update(state, 'PUSH', 1.0)
    
    assert result1.to_vector() == result2.to_vector(), "DETERMINISM VIOLATED"
    print("✓ Determinism verified")


if __name__ == '__main__':
    verify_determinism()
