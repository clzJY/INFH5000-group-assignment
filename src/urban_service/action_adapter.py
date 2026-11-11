"""Adapter for pinned EgoDeliveryRobot wheel dynamics, reverse disabled."""
import math


def apply_speed_cap(raw_action, decision, speed_m_s, *, reverse_enabled=False):
    raw = tuple(float(v) for v in raw_action)
    if len(raw) != 2 or not all(math.isfinite(v) for v in (*raw, speed_m_s)):
        raise ValueError("Expected finite two-dimensional action and speed")
    raw = tuple(max(-1.0, min(1.0, v)) for v in raw)
    # Baseline and fully released controller preserve the original action.
    if decision["state"] == "PASS":
        return raw
    if reverse_enabled:
        raise ValueError("Wheel speed adaptation requires enable_reverse=False")
    cap = decision["speed_cap_m_s"]
    if cap is None or cap < 0 or not math.isfinite(cap):
        raise ValueError("Invalid speed cap")
    if cap <= 1e-9:
        longitudinal = -1.0 if speed_m_s > 0.05 else min(0.0, raw[1])
    elif speed_m_s > cap:
        longitudinal = min(raw[1], -min(1.0, (speed_m_s - cap) * 2.0))
    else:
        # Do not request more forward acceleration than the base policy.
        longitudinal = min(raw[1], max(0.0, min(1.0, (cap - speed_m_s) * 2.0)))
    return raw[0], longitudinal
