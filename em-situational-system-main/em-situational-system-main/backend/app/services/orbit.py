"""Walker/TLE constellation generation and orbital propagation."""

from __future__ import annotations

import math
from datetime import datetime, timezone
from pathlib import Path

import httpx
import numpy as np
from skyfield.api import EarthSatellite, load, wgs84
from skyfield.framelib import itrs

from app.models.schemas import GroundStationModel, LinkConfigModel, LinkType, SatelliteModel


EARTH_RADIUS_KM = 6371.0
EARTH_RADIUS_M = EARTH_RADIUS_KM * 1000
SPEED_OF_LIGHT = 299792458.0
MU_EARTH = 3.986004418e14  # m^3/s^2
OMEGA_EARTH = 7.2921159e-5  # rad/s


def generate_walker_constellation(
    planes: int,
    sats_per_plane: int,
    altitude_km: float,
    inclination_deg: float,
    epoch: datetime,
) -> list[SatelliteModel]:
    """Generate Walker delta constellation metadata."""
    satellites: list[SatelliteModel] = []
    for p in range(planes):
        raan = 360.0 * p / planes
        for s in range(sats_per_plane):
            ma = 360.0 * s / sats_per_plane
            sid = f"sat_{p:02d}_{s:02d}"
            # Store orbital elements in TLE fields as placeholders
            satellites.append(SatelliteModel(
                id=sid,
                name=f"EMS-{sid}",
                tle_line1=f"ALT={altitude_km};INC={inclination_deg};RAAN={raan};MA={ma};EPOCH={epoch.isoformat()}",
                tle_line2=f"PLANE={p};SLOT={s}",
                orbit_plane=p,
            ))
    return satellites


def load_satellites_from_tle_text(tle_text: str, limit: int | None = None) -> list[SatelliteModel]:
    """Parse 3-line name/TLE blocks into satellite models."""
    lines = [line.strip() for line in tle_text.splitlines() if line.strip()]
    satellites: list[SatelliteModel] = []
    i = 0
    while i + 2 < len(lines):
        name, line1, line2 = lines[i], lines[i + 1], lines[i + 2]
        if line1.startswith("1 ") and line2.startswith("2 "):
            sat_id = name.lower().replace(" ", "_")
            satellites.append(SatelliteModel(
                id=sat_id,
                name=name,
                tle_line1=line1,
                tle_line2=line2,
                orbit_plane=0,
            ))
            if limit and len(satellites) >= limit:
                break
            i += 3
        else:
            i += 1
    return satellites


def load_satellites_from_tle_source(source: str, limit: int | None = None) -> list[SatelliteModel]:
    """Load TLE data from a local file path or HTTP(S) URL."""
    if source.startswith(("http://", "https://")):
        response = httpx.get(source, timeout=15.0, follow_redirects=True)
        response.raise_for_status()
        tle_text = response.text
    else:
        tle_text = Path(source).read_text(encoding="utf-8")
    satellites = load_satellites_from_tle_text(tle_text, limit=limit)
    if not satellites:
        raise ValueError(f"No valid TLE records found in source: {source}")
    return satellites


def _ecef_from_latlon(lat_deg: float, lon_deg: float, alt_m: float) -> np.ndarray:
    lat, lon = math.radians(lat_deg), math.radians(lon_deg)
    r = EARTH_RADIUS_M + alt_m
    return np.array([
        r * math.cos(lat) * math.cos(lon),
        r * math.cos(lat) * math.sin(lon),
        r * math.sin(lat),
    ])


def _geodetic_from_ecef(r: np.ndarray) -> tuple[float, float, float]:
    x, y, z = r
    lon = math.degrees(math.atan2(y, x))
    p = math.sqrt(x * x + y * y)
    lat = math.degrees(math.atan2(z, p))
    alt = np.linalg.norm(r) - EARTH_RADIUS_M
    return lat, lon, alt


class OrbitEngine:
    """Analytical circular-orbit propagation and link visibility."""

    def __init__(self, satellites: list[SatelliteModel], ground_stations: list[GroundStationModel],
                 altitude_km: float = 550, inclination_deg: float = 53, epoch: datetime | None = None):
        self.satellites = satellites
        self.ground_stations = {g.id: g for g in ground_stations}
        self.altitude_km = altitude_km
        self.inclination_deg = inclination_deg
        self.epoch = epoch or datetime.now(timezone.utc)
        if self.epoch.tzinfo is None:
            self.epoch = self.epoch.replace(tzinfo=timezone.utc)
        self._orbit_radius_m = (EARTH_RADIUS_KM + altitude_km) * 1000
        self._mean_motion = math.sqrt(MU_EARTH / self._orbit_radius_m ** 3)  # rad/s
        self._elements = self._parse_elements(satellites)
        self._timescale = load.timescale()
        self._tle_satellites = self._build_tle_satellites(satellites)
        for sat in satellites:
            if sat.omm:
                self._tle_satellites[sat.id] = EarthSatellite.from_omm(self._timescale, sat.omm)

    def _parse_elements(self, satellites: list[SatelliteModel]) -> dict[str, dict]:
        elements = {}
        for sat in satellites:
            l1 = sat.tle_line1
            alt = self.altitude_km
            inc = self.inclination_deg
            raan = 0.0
            ma = 0.0
            if l1.startswith("ALT="):
                parts = {kv.split("=")[0]: kv.split("=")[1] for kv in l1.split(";") if "=" in kv}
                alt = float(parts.get("ALT", alt))
                inc = float(parts.get("INC", inc))
                raan = float(parts.get("RAAN", raan))
                ma = float(parts.get("MA", ma))
            elements[sat.id] = {
                "altitude_km": alt,
                "inclination_deg": inc,
                "raan_deg": raan,
                "ma_deg": ma,
            }
        return elements

    @staticmethod
    def _build_tle_satellites(satellites: list[SatelliteModel]) -> dict[str, EarthSatellite]:
        tle_satellites: dict[str, EarthSatellite] = {}
        for sat in satellites:
            if sat.tle_line1.startswith("1 ") and sat.tle_line2.startswith("2 "):
                tle_satellites[sat.id] = EarthSatellite(sat.tle_line1, sat.tle_line2, sat.name)
        return tle_satellites

    def propagate(self, sat_id: str, when: datetime) -> dict:
        when = when.astimezone(timezone.utc) if when.tzinfo else when.replace(tzinfo=timezone.utc)
        tle_sat = self._tle_satellites.get(sat_id)
        if tle_sat is not None:
            return self._propagate_tle(tle_sat, sat_id, when)
        el = self._elements[sat_id]
        dt = (when - self.epoch).total_seconds()
        inc = math.radians(el["inclination_deg"])
        raan = math.radians(el["raan_deg"])
        ma0 = math.radians(el["ma_deg"])
        r = (EARTH_RADIUS_KM + el["altitude_km"]) * 1000
        n = math.sqrt(MU_EARTH / r ** 3)
        ma = ma0 + n * dt
        # Circular orbit position in ECI
        x_eci = r * (math.cos(raan) * math.cos(ma) - math.sin(raan) * math.sin(ma) * math.cos(inc))
        y_eci = r * (math.sin(raan) * math.cos(ma) + math.cos(raan) * math.sin(ma) * math.cos(inc))
        z_eci = r * math.sin(ma) * math.sin(inc)
        # Earth rotation to ECEF
        theta = OMEGA_EARTH * dt
        cos_t, sin_t = math.cos(theta), math.sin(theta)
        x = cos_t * x_eci + sin_t * y_eci
        y = -sin_t * x_eci + cos_t * y_eci
        z = z_eci
        ecef = np.array([x, y, z])
        lat, lon, alt = _geodetic_from_ecef(ecef)
        vel = r * n  # approximate
        return {
            "entity_id": sat_id,
            "latitude": lat,
            "longitude": lon,
            "altitude_m": alt,
            "velocity_m_s": vel,
            "ecef_m": ecef.tolist(),
        }

    def _propagate_tle(self, tle_sat: EarthSatellite, sat_id: str, when: datetime) -> dict:
        if getattr(self, "_cached_when", None) != when:
            self._cached_when = when
            self._cached_time = self._timescale.from_datetime(when)
        t = self._cached_time
        geocentric = tle_sat.at(t)
        subpoint = wgs84.subpoint(geocentric)
        ecef = geocentric.frame_xyz_and_velocity(itrs)
        position_m = ecef[0].m
        velocity_m_s = float(np.linalg.norm(ecef[1].m_per_s))
        return {
            "entity_id": sat_id,
            "latitude": subpoint.latitude.degrees,
            "longitude": subpoint.longitude.degrees,
            "altitude_m": subpoint.elevation.m,
            "velocity_m_s": velocity_m_s,
            "ecef_m": position_m.tolist(),
        }

    def build_isl_links(self, when: datetime, max_range_km: float = 5000) -> list[LinkConfigModel]:
        positions = {s.id: self.propagate(s.id, when) for s in self.satellites}
        links: list[LinkConfigModel] = []
        sat_ids = list(positions.keys())
        for i, sid in enumerate(sat_ids):
            ri = np.array(positions[sid]["ecef_m"])
            for sid2 in sat_ids[i + 1:]:
                dist_km = np.linalg.norm(ri - np.array(positions[sid2]["ecef_m"])) / 1000
                if dist_km <= max_range_km:
                    links.append(LinkConfigModel(
                        id=f"isl_{sid}_{sid2}",
                        link_type=LinkType.ISL,
                        source_id=sid,
                        target_id=sid2,
                        center_freq_hz=26e9,
                        bandwidth_hz=500e6,
                        tx_power_dbm=20,
                    ))
        return links

    def build_sgl_links(self, when: datetime, defaults: dict) -> list[LinkConfigModel]:
        links: list[LinkConfigModel] = []
        for sat in self.satellites:
            sp = self.propagate(sat.id, when)
            rs = np.array(sp["ecef_m"])
            for gs in self.ground_stations.values():
                rg = _ecef_from_latlon(gs.latitude, gs.longitude, gs.altitude_m)
                dist_km = np.linalg.norm(rs - rg) / 1000
                elev = self._elevation_deg(sp["latitude"], sp["longitude"], sp["altitude_m"],
                                           gs.latitude, gs.longitude, gs.altitude_m)
                if elev >= gs.visible_elevation_deg and dist_km < 3000:
                    links.append(LinkConfigModel(
                        id=f"sgl_{sat.id}_{gs.id}",
                        link_type=LinkType.SGL,
                        source_id=sat.id,
                        target_id=gs.id,
                        center_freq_hz=defaults.get("sgl_center_freq_hz", 14e9),
                        bandwidth_hz=defaults.get("sgl_bandwidth_hz", 200e6),
                        tx_power_dbm=defaults.get("sgl_tx_power_dbm", 30),
                    ))
        return links

    @staticmethod
    def _elevation_deg(slat, slon, salt, glat, glon, galt) -> float:
        rs = _ecef_from_latlon(slat, slon, salt)
        rg = _ecef_from_latlon(glat, glon, galt)
        diff = rs - rg
        dist = np.linalg.norm(diff)
        if dist < 1:
            return 90.0
        lat, lon = math.radians(glat), math.radians(glon)
        up = np.array([math.cos(lat) * math.cos(lon), math.cos(lat) * math.sin(lon), math.sin(lat)])
        cos_el = np.dot(diff / dist, up)
        return math.degrees(math.asin(max(-1, min(1, cos_el))))

    def link_geometry(self, source_pos: dict, target_pos: dict, freq_hz: float) -> dict:
        if "ecef_m" not in source_pos or "ecef_m" not in target_pos:
            return {"range_km": 0, "doppler_hz": 0, "delay_ms": 0, "visible": False}
        rs = np.array(source_pos["ecef_m"])
        rt = np.array(target_pos["ecef_m"])
        vs = source_pos.get("velocity_m_s", 0)
        vt = target_pos.get("velocity_m_s", 0)
        diff = rt - rs
        range_km = np.linalg.norm(diff) / 1000
        delay_ms = np.linalg.norm(diff) / SPEED_OF_LIGHT * 1000
        radial = (vs - vt) * 0.001
        doppler = freq_hz * radial / SPEED_OF_LIGHT if range_km > 0 else 0
        return {"range_km": range_km, "doppler_hz": doppler, "delay_ms": delay_ms, "visible": range_km > 0}
