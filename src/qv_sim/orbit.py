"""CelesTrak TLE / JSON OMM input and SGP4 propagation."""

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Protocol

from sgp4.api import Satrec, SGP4_ERRORS, jday
from sgp4 import omm

Vector3 = tuple[float, float, float]


def utc(time: datetime) -> datetime:
    if time.tzinfo is None or time.utcoffset() is None:
        raise ValueError("Time must include a timezone")
    return time.astimezone(timezone.utc)


def julian_date(time: datetime) -> tuple[float, float]:
    time = utc(time)
    return jday(time.year, time.month, time.day, time.hour, time.minute,
                time.second + time.microsecond / 1e6)


@dataclass(frozen=True)
class SatelliteState:
    satellite_id: str
    name: str
    time: datetime
    position_teme_km: Vector3
    velocity_teme_km_s: Vector3
    frame: str = "TEME"


class OrbitProvider(Protocol):
    """Future analytical Walker providers implement this same interface."""

    def states_at(self, time: datetime) -> list[SatelliteState]: ...


class Sgp4Constellation:
    def __init__(self, satellites: list[tuple[str, Satrec]]):
        if not satellites:
            raise ValueError("Constellation is empty")
        ids = [sat.satnum for _, sat in satellites]
        if len(ids) != len(set(ids)):
            raise ValueError("Duplicate satellite IDs")
        self._satellites = tuple(satellites)

    @classmethod
    def from_file(cls, path: str | Path) -> "Sgp4Constellation":
        """Read a local snapshot: .json for CelesTrak OMM, otherwise TLE."""
        path = Path(path)
        text = path.read_text(encoding="utf-8-sig")
        if path.suffix.lower() == ".json":
            records = json.loads(text)
            if not isinstance(records, list):
                raise ValueError("OMM JSON must be an array of records")
            satellites = []
            for fields in records:
                for key, expected in (("CENTER_NAME", "EARTH"),
                                      ("REF_FRAME", "TEME"),
                                      ("TIME_SYSTEM", "UTC"),
                                      ("MEAN_ELEMENT_THEORY", "SGP4")):
                    if fields.get(key, expected) != expected:
                        raise ValueError(f"Unsupported OMM {key}")
                sat = Satrec()
                omm.initialize(sat, fields)
                satellites.append((fields.get("OBJECT_NAME", str(sat.satnum)), sat))
            return cls(satellites)
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        satellites = []
        i = 0
        while i < len(lines):
            name = None
            if not lines[i].startswith("1 "):
                name = lines[i].removeprefix("0 ")
                i += 1
            if i + 1 >= len(lines) or not lines[i].startswith("1 ") or not lines[i + 1].startswith("2 "):
                raise ValueError(f"Invalid TLE pair near nonempty line {i + 1}")
            first, second = lines[i:i + 2]
            if first[2:7] != second[2:7]:
                raise ValueError("TLE satellite IDs do not match")
            sat = Satrec.twoline2rv(first, second)
            satellites.append((name or str(sat.satnum), sat))
            i += 2
        return cls(satellites)

    def states_at(self, time: datetime) -> list[SatelliteState]:
        time = utc(time)
        jd, fraction = julian_date(time)
        result = []
        for name, sat in self._satellites:
            error, position, velocity = sat.sgp4(jd, fraction)
            if error:
                raise ValueError(f"SGP4 satellite {sat.satnum}: {SGP4_ERRORS[error]}")
            result.append(SatelliteState(str(sat.satnum), name, time, position, velocity))
        return result
