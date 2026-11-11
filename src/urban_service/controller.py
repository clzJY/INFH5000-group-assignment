"""Heuristic speed cap, with no collision-free or human-comfort guarantee."""
from dataclasses import dataclass
import math


@dataclass(frozen=True)
class Actor:
    actor_id: str
    position: tuple[float, float]
    velocity: tuple[float, float]
    radius: float
    kind: str = "pedestrian"

    def __post_init__(self):
        if len(self.position) != 2 or len(self.velocity) != 2 or not all(math.isfinite(v) for v in (*self.position, *self.velocity, self.radius)) or self.radius <= 0:
            raise ValueError("Invalid finite actor geometry/state")


@dataclass(frozen=True)
class YieldConfig:
    mode: str = "baseline"
    horizon_s: float = 2.0
    stop_clearance_m: float = 0.5
    slow_clearance_m: float = 1.5
    release_margin_m: float = 0.25
    release_hold_s: float = 0.5
    recovery_accel_m_s2: float = 1.0
    max_speed_m_s: float = 2.0

    def __post_init__(self):
        if self.mode not in ("baseline", "distance", "predictive"):
            raise ValueError("Unknown controller mode")
        values = [v for k, v in vars(self).items() if k != "mode"]
        if not all(math.isfinite(v) for v in values):
            raise ValueError("Nonfinite controller parameter")
        if not (0 <= self.stop_clearance_m < self.slow_clearance_m and
                self.horizon_s > 0 and self.max_speed_m_s > 0 and
                self.recovery_accel_m_s2 > 0 and self.release_hold_s >= 0 and self.release_margin_m >= 0):
            raise ValueError("Invalid controller parameters")


def clearance(a: Actor, b: Actor) -> float:
    """Signed separation of conservative enclosing circles, not mesh distance."""
    return math.dist(a.position, b.position) - a.radius - b.radius


def closest_approach(a: Actor, b: Actor, horizon_s: float) -> tuple[float, float]:
    p = tuple(y - x for x, y in zip(a.position, b.position))
    w = tuple(y - x for x, y in zip(a.velocity, b.velocity))
    w2 = sum(x * x for x in w)
    t = 0.0 if w2 < 1e-12 else max(0.0, min(horizon_s, -sum(x * y for x, y in zip(p, w)) / w2))
    d = math.hypot(*(x + t * y for x, y in zip(p, w))) - a.radius - b.radius
    return t, d


class YieldController:
    def __init__(self, config: YieldConfig):
        self.config = config
        self.waiting = False
        self.clear_elapsed = 0.0
        self.previous_cap = config.max_speed_m_s

    def update(self, ego: Actor, pedestrians: list[Actor], dt: float) -> dict:
        if dt <= 0 or not math.isfinite(dt):
            raise ValueError("dt must be finite and positive")
        c = self.config
        current = min((clearance(ego, p) for p in pedestrians), default=math.inf)
        risk = current
        if c.mode == "predictive":
            risk = min((closest_approach(ego, p, c.horizon_s)[1] for p in pedestrians), default=math.inf)
        if c.mode == "baseline":
            return dict(state="PASS", speed_cap_m_s=None,
                        clearance_m=current if math.isfinite(current) else None, risk_clearance_m=None)
        if c.mode == "predictive":
            if risk <= c.stop_clearance_m:
                self.waiting = True
                self.clear_elapsed = 0.0
            elif self.waiting:
                if risk > c.stop_clearance_m + c.release_margin_m:
                    self.clear_elapsed += dt
                    if self.clear_elapsed + 1e-12 >= c.release_hold_s:
                        self.waiting = False
                else:
                    self.clear_elapsed = 0.0
        ratio = max(0.0, min(1.0, (risk - c.stop_clearance_m) /
                              (c.slow_clearance_m - c.stop_clearance_m)))
        target = 0.0 if self.waiting else c.max_speed_m_s * ratio
        if c.mode == "predictive":
            # Slow-down is immediate; only recovery is smoothed.
            target = min(target, self.previous_cap + c.recovery_accel_m_s2 * dt)
        self.previous_cap = target
        return dict(state="WAIT" if target <= 1e-9 else "SLOW" if target < c.max_speed_m_s else "PASS",
                    speed_cap_m_s=target,
                    clearance_m=current if math.isfinite(current) else None,
                    risk_clearance_m=risk if math.isfinite(risk) else None)


class PoseTracker:
    """Velocities derived in a single simulator coordinate frame, using decision dt."""
    def __init__(self):
        self.previous = {}

    def snapshot(self, states: list[dict], dt: float) -> list[Actor]:
        if dt <= 0:
            raise ValueError("dt must be positive")
        result = []
        positions = {}
        for state in states:
            key = state["actor_id"]
            pos = tuple(float(v) for v in state["position"][:2])
            old = self.previous.get(key)
            velocity = (0.0, 0.0) if old is None else tuple((v - u) / dt for u, v in zip(old, pos))
            result.append(Actor(key, pos, velocity, state["radius"], state.get("kind", "pedestrian")))
            positions[key] = pos
        self.previous = positions
        return result
