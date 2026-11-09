"""Circular two-body Walker Delta in a fixed mean-equator-of-epoch frame.

For short experiments the visibility layer approximates this frame as the
mean equator of date. No precession, nutation or J2 is modeled.
"""
from dataclasses import dataclass
from datetime import datetime
from math import cos, sin, radians, sqrt, isfinite

from .orbit import SatelliteState, utc


@dataclass(frozen=True)
class WalkerDelta:
    epoch: datetime
    total: int = 120
    planes: int = 12
    phasing: int = 1
    inclination_deg: float = 53.0
    altitude_km: float = 550.0
    raan_offset_deg: float = 0.0
    phase_offset_deg: float = 0.0

    def __post_init__(self):
        utc(self.epoch)
        if any(type(x) is not int for x in (self.total, self.planes, self.phasing)):
            raise ValueError("Walker counts and phasing must be integers")
        if self.total <= 0 or self.planes <= 0 or self.total % self.planes:
            raise ValueError("Total must be positive and divisible by planes")
        if not 0 <= self.phasing < self.planes:
            raise ValueError("Phasing must satisfy 0 <= F < P")
        if not all(isfinite(x) for x in (self.inclination_deg, self.altitude_km,
                                         self.raan_offset_deg, self.phase_offset_deg)):
            raise ValueError("Walker parameters must be finite")
        if not 0 <= self.inclination_deg <= 180 or self.altitude_km <= 0:
            raise ValueError("Invalid inclination or altitude")

    def states_at(self, time: datetime) -> list[SatelliteState]:
        time = utc(time)
        dt = (time - utc(self.epoch)).total_seconds()
        radius = 6378.137 + self.altitude_km
        n = sqrt(398600.4418 / radius**3)
        inc = radians(self.inclination_deg)
        per_plane = self.total // self.planes
        states = []
        for p in range(self.planes):
            node = radians(self.raan_offset_deg + 360 * p / self.planes)
            a = (cos(node), sin(node), 0.0)
            b = (-sin(node)*cos(inc), cos(node)*cos(inc), sin(inc))
            for s in range(per_plane):
                u = radians(self.phase_offset_deg + 360*s/per_plane
                            + 360*self.phasing*p/self.total) + n*dt
                pos = tuple(radius*(cos(u)*a[k] + sin(u)*b[k]) for k in range(3))
                vel = tuple(radius*n*(-sin(u)*a[k] + cos(u)*b[k]) for k in range(3))
                identifier = f"W{p:02d}-{s:02d}"
                states.append(SatelliteState(identifier, identifier, time, pos, vel,
                                             "MEAN_EQUATOR_OF_EPOCH"))
        return states
