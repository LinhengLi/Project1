"""WGS84 site geometry with an approximate TEME-to-Earth-fixed rotation.

Uses UTC as UT1 and neglects polar motion. Suitable for initial geometric
screening, not precision pointing or regulatory interference certification.
"""

from dataclasses import dataclass
from math import atan2, cos, degrees, isfinite, radians, sin, sqrt

from .orbit import SatelliteState, Vector3, julian_date


@dataclass(frozen=True)
class GroundSite:
    site_id: str
    latitude_deg: float
    longitude_deg: float
    altitude_km: float = 0.0
    min_elevation_deg: float = 10.0

    def __post_init__(self):
        if not all(isfinite(x) for x in (self.latitude_deg, self.longitude_deg,
                                        self.altitude_km, self.min_elevation_deg)):
            raise ValueError("Site coordinates must be finite")
        if not -90 <= self.latitude_deg <= 90 or not -180 <= self.longitude_deg <= 180:
            raise ValueError("Invalid latitude or longitude")
        if not 0 <= self.min_elevation_deg <= 90:
            raise ValueError("Elevation mask must be between 0 and 90 degrees")

    def position_ecef_km(self) -> Vector3:
        lat, lon = radians(self.latitude_deg), radians(self.longitude_deg)
        e2 = 6.6943799901413165e-3
        n = 6378.137 / sqrt(1 - e2 * sin(lat) ** 2)
        return ((n + self.altitude_km) * cos(lat) * cos(lon),
                (n + self.altitude_km) * cos(lat) * sin(lon),
                (n * (1 - e2) + self.altitude_km) * sin(lat))


@dataclass(frozen=True)
class Visibility:
    satellite_id: str
    site_id: str
    azimuth_deg: float
    elevation_deg: float
    slant_range_km: float
    visible: bool


def teme_to_ecef(state: SatelliteState) -> Vector3:
    if state.frame not in ("TEME", "MEAN_EQUATOR_OF_EPOCH"):
        raise ValueError(f"Unsupported frame: {state.frame}")
    jd, fraction = julian_date(state.time)
    days = (jd - 2451545.0) + fraction
    t = days / 36525.0
    angle = radians((280.46061837 + 360.98564736629 * days
                     + 0.000387933 * t * t - t ** 3 / 38710000) % 360)
    x, y, z = state.position_teme_km
    return cos(angle) * x + sin(angle) * y, -sin(angle) * x + cos(angle) * y, z


def observe(site: GroundSite, state: SatelliteState) -> Visibility:
    satellite = teme_to_ecef(state)
    ground = site.position_ecef_km()
    dx, dy, dz = (satellite[i] - ground[i] for i in range(3))
    lat, lon = radians(site.latitude_deg), radians(site.longitude_deg)
    east = -sin(lon) * dx + cos(lon) * dy
    north = -sin(lat) * cos(lon) * dx - sin(lat) * sin(lon) * dy + cos(lat) * dz
    up = cos(lat) * cos(lon) * dx + cos(lat) * sin(lon) * dy + sin(lat) * dz
    distance = sqrt(east ** 2 + north ** 2 + up ** 2)
    if distance == 0:
        raise ValueError("Satellite coincides with ground site")
    elevation = degrees(atan2(up, sqrt(east ** 2 + north ** 2)))
    return Visibility(state.satellite_id, site.site_id,
                      degrees(atan2(east, north)) % 360, elevation,
                      distance, elevation >= site.min_elevation_deg)
