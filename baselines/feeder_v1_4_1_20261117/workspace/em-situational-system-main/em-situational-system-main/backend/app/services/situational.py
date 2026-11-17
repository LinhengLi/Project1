"""Electromagnetic situational awareness generation."""

from __future__ import annotations

import random
from datetime import datetime

import numpy as np

from app.models.schemas import (
    LinkState,
    RiskLevel,
    ScenarioConfig,
    SpectrumGrid,
    SituationalSnapshot,
)
from app.services.orbit import OrbitEngine
from app.services.propagation import PropagationEngine
from app.services.real_data import RealObservationRepository


class SituationalEngine:
    """Generate multi-dimensional EM situational snapshots."""

    FREQ_START = 12e9
    FREQ_END = 28e9
    NUM_BINS = 64

    def __init__(
        self,
        orbit: OrbitEngine,
        propagation: PropagationEngine,
        scenario: ScenarioConfig,
        real_observations: RealObservationRepository | None = None,
    ):
        self.orbit = orbit
        self.propagation = propagation
        self.scenario = scenario
        self.real_observations = real_observations or RealObservationRepository()

    def _build_links(self, when: datetime) -> list[LinkState]:
        if self.scenario.orbit_only:
            return []
        defaults = self.scenario.default_links
        isl = self.orbit.build_isl_links(when, max_range_km=2500)
        sgl = self.orbit.build_sgl_links(when, defaults)
        isl = isl[:200]
        all_links = isl + sgl
        links = [self.propagation.compute_link_state(link, when) for link in all_links]
        return self.real_observations.apply_link_observations(when, links)

    def _build_spectrum_grid(self, links: list[LinkState], when: datetime) -> SpectrumGrid:
        bins = np.linspace(self.FREQ_START, self.FREQ_END, self.NUM_BINS)
        power = np.full(self.NUM_BINS, -120.0)

        for link in links:
            if not link.visible:
                continue
            idx = int((link.center_freq_hz - self.FREQ_START) / (self.FREQ_END - self.FREQ_START) * (self.NUM_BINS - 1))
            idx = max(0, min(self.NUM_BINS - 1, idx))
            bw_bins = max(1, int(link.bandwidth_hz / (self.FREQ_END - self.FREQ_START) * self.NUM_BINS))
            for j in range(max(0, idx - bw_bins), min(self.NUM_BINS, idx + bw_bins + 1)):
                power[j] = max(power[j], link.rx_power_dbm)

        for jammer in self.scenario.jammers:
            j_idx = int((jammer.center_freq_hz - self.FREQ_START) / (self.FREQ_END - self.FREQ_START) * (self.NUM_BINS - 1))
            j_idx = max(0, min(self.NUM_BINS - 1, j_idx))
            j_power = jammer.tx_power_dbm - 60
            for j in range(max(0, j_idx - 2), min(self.NUM_BINS, j_idx + 3)):
                power[j] = max(power[j], j_power)

        return SpectrumGrid(
            freq_bins_hz=bins.tolist(),
            power_dbm=power.tolist(),
            observed_mask=[True] * self.NUM_BINS,
        )

    def generate(self, when: datetime) -> SituationalSnapshot:
        links = self._build_links(when)
        simulated_grid = self._build_spectrum_grid(links, when)
        grid = self.real_observations.spectrum_grid(when, simulated_grid)
        jammer_info = [
            {"id": j.id, "name": j.name, "style": j.jamming_style.value, "type": j.source_type.value}
            for j in self.scenario.jammers
        ]
        explanation = self._build_explanation(links, jammer_info)
        return SituationalSnapshot(
            timestamp=when,
            scenario_id=self.scenario.scenario_id,
            links=links,
            spectrum_grid=grid,
            jammers=jammer_info,
            explanation=explanation,
        )

    def apply_sparse_observation(self, snap: SituationalSnapshot, rate: float) -> SituationalSnapshot:
        if not snap.spectrum_grid:
            return snap
        n = len(snap.spectrum_grid.freq_bins_hz)
        k = max(1, int(n * rate))
        rng = random.Random(42)
        observed = [False] * n
        indices = rng.sample(range(n), k)
        for i in indices:
            observed[i] = True
        masked_power = [
            p if observed[i] else -999.0
            for i, p in enumerate(snap.spectrum_grid.power_dbm)
        ]
        snap.spectrum_grid = SpectrumGrid(
            freq_bins_hz=snap.spectrum_grid.freq_bins_hz,
            power_dbm=masked_power,
            observed_mask=observed,
        )
        for link in snap.links:
            if rng.random() > rate:
                link.confidence = 0.3
        return snap

    def _build_explanation(self, links: list[LinkState], jammers: list[dict]) -> str:
        bad = [link for link in links if link.risk_level != RiskLevel.NORMAL and link.visible]
        if not bad:
            return "当前态势正常，未检测到显著电磁干扰影响。"
        worst = min(bad, key=lambda link: link.sinr_db)
        jam_names = ", ".join(jammer["name"] or jammer["id"] for jammer in jammers[:3])
        return (
            f"链路 {worst.link_id} SINR={worst.sinr_db:.1f}dB，风险等级 {worst.risk_level.value}。"
            f"可能受到干扰源 [{jam_names}] 影响，建议重点关注 "
            f"{self.FREQ_START / 1e9:.0f}-{self.FREQ_END / 1e9:.0f}GHz 频段。"
        )
