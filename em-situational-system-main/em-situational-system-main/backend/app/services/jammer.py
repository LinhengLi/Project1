"""Multi-source electromagnetic jammer modeling."""

from __future__ import annotations

import math
from datetime import datetime

from app.models.schemas import JammerModel, JammingStyle


def jammer_position_at(jammer: JammerModel, when: datetime) -> tuple[float, float, float]:
    if not jammer.trajectory:
        return jammer.latitude, jammer.longitude, jammer.altitude_m
    # Linear interpolation along trajectory waypoints
    ts = when.timestamp()
    best = (jammer.latitude, jammer.longitude, jammer.altitude_m)
    for wp in jammer.trajectory:
        try:
            from datetime import datetime as dt
            t = dt.fromisoformat(wp["time"].replace("Z", "+00:00")).timestamp()
            if t <= ts:
                best = (wp["latitude"], wp["longitude"], wp.get("altitude_m", 0))
        except (KeyError, ValueError):
            continue
    return best


def effective_jamming_bandwidth(style: JammingStyle, configured_bw: float) -> float:
    factors = {
        JammingStyle.CO_CHANNEL: 1.0,
        JammingStyle.ADJACENT_CHANNEL: 0.3,
        JammingStyle.BARRAGE: 2.0,
        JammingStyle.NARROWBAND_SPOT: 0.05,
        JammingStyle.SWEEP: 1.5,
        JammingStyle.PULSE: 0.5,
        JammingStyle.DECEPTIVE: 0.2,
        JammingStyle.NOISE: 1.0,
        JammingStyle.BURST_COLLISION: 0.8,
    }
    return configured_bw * factors.get(style, 1.0)


class JammerEngine:
    """Compute jammer contribution at receiver."""

    def __init__(self, jammers: list[JammerModel]):
        self.jammers = jammers

    def jammer_ecef(self, jammer: JammerModel, when: datetime):
        import numpy as np
        lat, lon, alt = jammer_position_at(jammer, when)
        lat_r, lon_r = math.radians(lat), math.radians(lon)
        r = 6371000 + alt
        return np.array([
            r * math.cos(lat_r) * math.cos(lon_r),
            r * math.cos(lat_r) * math.sin(lon_r),
            r * math.sin(lat_r),
        ])

    def interference_power_dbm(
        self,
        jammer: JammerModel,
        rx_ecef,
        link_freq_hz: float,
        link_bw_hz: float,
        when: datetime,
    ) -> float:
        """Received jamming power at receiver (simplified)."""
        import numpy as np
        j_ecef = self.jammer_ecef(jammer, when)
        dist_m = max(np.linalg.norm(rx_ecef - j_ecef), 1.0)
        dist_km = dist_m / 1000

        # Free space path loss
        fspl = 20 * math.log10(dist_m) + 20 * math.log10(jammer.center_freq_hz) - 147.55

        # Frequency coupling
        eff_bw = effective_jamming_bandwidth(jammer.jamming_style, jammer.bandwidth_hz)
        freq_offset = abs(jammer.center_freq_hz - link_freq_hz)
        if jammer.jamming_style.value == "sweep":
            freq_coupling_db = -3  # sweep covers band
        elif freq_offset > (eff_bw + link_bw_hz) / 2:
            freq_coupling_db = -40
        elif freq_offset < link_bw_hz * 0.1:
            freq_coupling_db = 0
        else:
            freq_coupling_db = -10 * (freq_offset / link_bw_hz)

        style_gain = {
            "co_channel": 0, "barrage": 3, "deceptive": -5,
            "pulse": -8, "noise": -2, "narrowband_spot": -15 if freq_offset > link_bw_hz else 0,
        }.get(jammer.jamming_style.value, -5)

        rx_power = (
            jammer.tx_power_dbm + jammer.antenna_gain_dbi
            - fspl + freq_coupling_db + style_gain
        )
        return rx_power

    def total_interference_dbm(self, rx_ecef, link_freq_hz: float, link_bw_hz: float,
                               when: datetime) -> tuple[float, list[str]]:
        """Combine multiple jammers (power sum in linear domain)."""
        import numpy as np
        active_jammers = []
        linear_sum = 0.0
        for jammer in self.jammers:
            p_dbm = self.interference_power_dbm(jammer, rx_ecef, link_freq_hz, link_bw_hz, when)
            if p_dbm > -120:
                linear_sum += 10 ** (p_dbm / 10)
                active_jammers.append(jammer.id)
        if linear_sum <= 0:
            return -999.0, []
        total_dbm = 10 * math.log10(linear_sum)
        return total_dbm, active_jammers
