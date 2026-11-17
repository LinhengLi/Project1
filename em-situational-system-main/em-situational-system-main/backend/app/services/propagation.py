"""Electromagnetic propagation and SINR calculation."""

from __future__ import annotations

import math

from app.models.schemas import LinkConfigModel, LinkState, LinkType, RiskLevel
from app.services.jammer import JammerEngine
from app.services.orbit import OrbitEngine, _ecef_from_latlon


NOISE_FLOOR_DBM = -110  # receiver noise floor approx


def free_space_path_loss_db(dist_m: float, freq_hz: float) -> float:
    return 20 * math.log10(max(dist_m, 1)) + 20 * math.log10(freq_hz) - 147.55


def sinr_to_risk(sinr_db: float) -> RiskLevel:
    if sinr_db < 0:
        return RiskLevel.UNAVAILABLE
    if sinr_db < 5:
        return RiskLevel.SEVERE
    if sinr_db < 10:
        return RiskLevel.MODERATE
    if sinr_db < 15:
        return RiskLevel.MILD
    return RiskLevel.NORMAL


class PropagationEngine:
    """Compute link budget and SINR."""

    def __init__(self, orbit: OrbitEngine, jammer_engine: JammerEngine):
        self.orbit = orbit
        self.jammer_engine = jammer_engine

    def compute_link_state(
        self,
        link: LinkConfigModel,
        when,
        source_pos: dict | None = None,
        target_pos: dict | None = None,
    ) -> LinkState:
        if source_pos is None:
            source_pos = self.orbit.propagate(link.source_id, when)
        if link.link_type == LinkType.SGL:
            gs = self.orbit.ground_stations.get(link.target_id)
            if gs is None:
                return LinkState(link_id=link.id, link_type=link.link_type,
                                 source_id=link.source_id, target_id=link.target_id, visible=False)
            target_pos = {
                "ecef_m": _ecef_from_latlon(gs.latitude, gs.longitude, gs.altitude_m).tolist(),
                "latitude": gs.latitude, "longitude": gs.longitude, "altitude_m": gs.altitude_m,
                "velocity_m_s": 0,
            }
        elif target_pos is None:
            target_pos = self.orbit.propagate(link.target_id, when)

        geom = self.orbit.link_geometry(source_pos, target_pos, link.center_freq_hz)
        if not geom["visible"]:
            return LinkState(
                link_id=link.id, link_type=link.link_type,
                source_id=link.source_id, target_id=link.target_id, visible=False,
            )

        dist_m = geom["range_km"] * 1000
        fspl = free_space_path_loss_db(dist_m, link.center_freq_hz)
        tx_gain = 15 if link.link_type == LinkType.ISL else 30
        rx_gain = 30
        rx_power = link.tx_power_dbm + tx_gain + rx_gain - fspl

        import numpy as np
        rx_ecef = np.array(target_pos["ecef_m"])
        intf_dbm, jammer_ids = self.jammer_engine.total_interference_dbm(
            rx_ecef, link.center_freq_hz, link.bandwidth_hz, when
        )

        # SINR: signal / (interference + noise)
        def to_linear(dbm):
            return 10 ** (dbm / 10) if dbm > -200 else 0

        sig = to_linear(rx_power)
        intf = to_linear(intf_dbm) if intf_dbm > -200 else 0
        noise = to_linear(NOISE_FLOOR_DBM)
        sinr_linear = sig / (intf + noise + 1e-30)
        sinr_db = 10 * math.log10(max(sinr_linear, 1e-30))

        elev = self.orbit._elevation_deg(
            source_pos["latitude"], source_pos["longitude"], source_pos["altitude_m"],
            target_pos["latitude"], target_pos["longitude"], target_pos["altitude_m"],
        ) if link.link_type == LinkType.SGL else 0

        return LinkState(
            link_id=link.id,
            link_type=link.link_type,
            source_id=link.source_id,
            target_id=link.target_id,
            visible=True,
            center_freq_hz=link.center_freq_hz,
            bandwidth_hz=link.bandwidth_hz,
            range_km=geom["range_km"],
            elevation_deg=elev,
            doppler_hz=geom["doppler_hz"],
            propagation_delay_ms=geom["delay_ms"],
            rx_power_dbm=rx_power,
            interference_power_dbm=intf_dbm,
            sinr_db=sinr_db,
            risk_level=sinr_to_risk(sinr_db),
            confidence=1.0,
        )
