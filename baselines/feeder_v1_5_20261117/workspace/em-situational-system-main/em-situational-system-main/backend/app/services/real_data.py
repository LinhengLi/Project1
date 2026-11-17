"""Adapters for externally imported real observation datasets."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

import numpy as np

from app.models.schemas import LinkState, RiskLevel, SpectrumGrid
from app.services.propagation import sinr_to_risk


_TIMESTAMP_KEYS = ("timestamp", "time", "datetime", "observed_at")
_FREQ_KEYS = ("freq_hz", "frequency_hz", "center_freq_hz", "frequency")
_POWER_KEYS = ("power_dbm", "psd_dbm", "rx_power_dbm", "value_dbm")


def _as_float(value: Any, default: float = 0.0) -> float:
    if value in (None, ""):
        return default
    return float(value)


def _as_datetime(value: Any) -> datetime | None:
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc) if value.tzinfo else value.replace(tzinfo=timezone.utc)
    text = str(value).strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    return parsed.astimezone(timezone.utc) if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _first(record: dict[str, Any], keys: tuple[str, ...], default: Any = None) -> Any:
    for key in keys:
        if key in record:
            return record[key]
    return default


def _record_time(record: dict[str, Any]) -> datetime | None:
    return _as_datetime(_first(record, _TIMESTAMP_KEYS))


def _nearest_records(records: list[dict[str, Any]], when: datetime, tolerance_sec: float | None) -> list[dict[str, Any]]:
    if not records:
        return []
    when = when.astimezone(timezone.utc) if when.tzinfo else when.replace(tzinfo=timezone.utc)
    timeless = [record for record in records if _record_time(record) is None]
    timed = [(abs((_record_time(record) - when).total_seconds()), record) for record in records if _record_time(record) is not None]
    if not timed:
        return timeless
    min_delta = min(delta for delta, _ in timed)
    if tolerance_sec is not None and min_delta > tolerance_sec:
        return timeless
    nearest = [record for delta, record in timed if abs(delta - min_delta) < 1e-6]
    return timeless + nearest


class RealObservationRepository:
    """Holds real external observations and projects them into the simulation state."""

    def __init__(
        self,
        spectrum_records: list[dict[str, Any]] | None = None,
        link_records: list[dict[str, Any]] | None = None,
        tolerance_sec: float | None = 300.0,
    ):
        self.spectrum_records = spectrum_records or []
        self.link_records = link_records or []
        self.tolerance_sec = tolerance_sec

    def has_spectrum(self) -> bool:
        return bool(self.spectrum_records)

    def has_links(self) -> bool:
        return bool(self.link_records)

    def spectrum_grid(self, when: datetime, fallback_grid: SpectrumGrid) -> SpectrumGrid:
        records = _nearest_records(self.spectrum_records, when, self.tolerance_sec)
        if not records:
            return fallback_grid

        bins = np.array(fallback_grid.freq_bins_hz, dtype=float)
        grouped: dict[int, list[float]] = defaultdict(list)
        for record in records:
            freq = _first(record, _FREQ_KEYS)
            power = _first(record, _POWER_KEYS)
            if freq in (None, "") or power in (None, ""):
                continue
            idx = int(np.abs(bins - _as_float(freq)).argmin())
            grouped[idx].append(_as_float(power))

        if not grouped:
            return fallback_grid

        power = [-999.0] * len(bins)
        observed = [False] * len(bins)
        for idx, values in grouped.items():
            power[idx] = float(np.mean(values))
            observed[idx] = True

        return SpectrumGrid(
            freq_bins_hz=bins.tolist(),
            power_dbm=power,
            observed_mask=observed,
            completed=False,
            completion_method="real_observation",
        )

    def apply_link_observations(self, when: datetime, links: list[LinkState]) -> list[LinkState]:
        records = _nearest_records(self.link_records, when, self.tolerance_sec)
        if not records:
            return links

        by_id = {str(record.get("link_id")): record for record in records if record.get("link_id")}
        if not by_id:
            return links

        updated: list[LinkState] = []
        for link in links:
            record = by_id.get(link.link_id)
            if not record:
                updated.append(link)
                continue
            patch = link.model_dump()
            for field in (
                "visible",
                "center_freq_hz",
                "bandwidth_hz",
                "range_km",
                "elevation_deg",
                "doppler_hz",
                "propagation_delay_ms",
                "rx_power_dbm",
                "interference_power_dbm",
                "sinr_db",
                "confidence",
            ):
                if field in record and record[field] not in (None, ""):
                    if field == "visible":
                        patch[field] = str(record[field]).lower() not in ("false", "0", "no")
                    else:
                        patch[field] = _as_float(record[field], patch[field])
            if record.get("risk_level"):
                patch["risk_level"] = RiskLevel(str(record["risk_level"]).lower())
            elif "sinr_db" in record and record["sinr_db"] not in (None, ""):
                patch["risk_level"] = sinr_to_risk(_as_float(record["sinr_db"])).value
            updated.append(LinkState(**patch))
        return updated
