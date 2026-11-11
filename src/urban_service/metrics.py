"""Episode metrics with missing pedestrian measurements represented as null."""
import math
from .controller import Actor, clearance


class EpisodeMetrics:
    def __init__(self, initial_position, near_clearance_m=1.0):
        self.last_position = tuple(initial_position)
        self.near_clearance_m = near_clearance_m
        self.steps = 0
        self.duration_s = self.path_length_m = self.near_s = self.observed_s = self.wait_s = 0.0
        self.min_clearance = None
        self.human_collision = False
        self.any_collision = False
        self.ego_trace = [tuple(initial_position)]

    def update(self, ego: Actor, pedestrians: list[Actor], dt, info: dict, controller_state: str):
        if dt <= 0 or not math.isfinite(dt):
            raise ValueError("Invalid dt")
        self.steps += 1
        self.duration_s += dt
        self.path_length_m += math.dist(self.last_position, ego.position)
        self.last_position = ego.position
        self.ego_trace.append(ego.position)
        if pedestrians:
            d = min(clearance(ego, p) for p in pedestrians)
            self.min_clearance = d if self.min_clearance is None else min(d, self.min_clearance)
            self.observed_s += dt
            if d < self.near_clearance_m:
                self.near_s += dt
        self.wait_s += dt if controller_state == "WAIT" else 0.0
        self.human_collision |= bool(info.get("crash_human", False))
        self.any_collision |= any(bool(info.get(k, False)) for k in
                                  ("crash_human", "crash_vehicle", "crash_object", "crash_building", "crash_sidewalk"))

    def summary(self, success, timeout, error=None):
        return dict(navigation_success=bool(success),
                    collision_free_success=bool(success and not self.any_collision),
                    pedestrian_collision=self.human_collision, any_collision=self.any_collision,
                    steps=self.steps, duration_s=self.duration_s, path_length_m=self.path_length_m,
                    min_clearance_m=self.min_clearance,
                    near_time_fraction=self.near_s / self.duration_s if self.duration_s else None,
                    pedestrian_observed_time_s=self.observed_s, wait_time_s=self.wait_s,
                    timeout=bool(timeout), error=error)
