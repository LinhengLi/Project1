"""Risk assessment and alerting engine."""

from __future__ import annotations

import uuid
from datetime import datetime

from app.models.schemas import (
    AlertTrace,
    DownstreamAlert,
    LinkState,
    RiskLevel,
    ScenarioConfig,
    SituationalSnapshot,
)
from app.services.knowledge import explain_link_degradation


class RiskEngine:
    """5-dimensional risk assessment: link, frequency, region, satellite, business."""

    def __init__(self, scenario: ScenarioConfig):
        self.scenario = scenario

    def evaluate(self, snap: SituationalSnapshot, predictive: bool = False) -> list[DownstreamAlert]:
        alerts: list[DownstreamAlert] = []
        for link in snap.links:
            if not link.visible:
                continue
            if link.risk_level in (RiskLevel.SEVERE, RiskLevel.UNAVAILABLE, RiskLevel.MODERATE):
                alert_type = "predictive" if predictive else "realtime"
                if link.risk_level == RiskLevel.UNAVAILABLE:
                    alert_type = "link_degradation"
                trace = self._trace(link, snap)
                alerts.append(DownstreamAlert(
                    alert_id=str(uuid.uuid4())[:8],
                    alert_type=alert_type,
                    timestamp=snap.timestamp,
                    risk_level=link.risk_level,
                    affected_links=[link.link_id],
                    affected_freq_hz=[link.center_freq_hz] if link.center_freq_hz else [],
                    recommended_freq_hz=self._recommend_freq(link),
                    prediction_confidence=link.confidence,
                    trace=trace,
                ))

        # Spectrum conflict alerts
        freq_map: dict[float, list[str]] = {}
        for link in snap.links:
            if link.visible and link.center_freq_hz:
                bucket = round(link.center_freq_hz / 1e8) * 1e8
                freq_map.setdefault(bucket, []).append(link.link_id)
        for freq, links in freq_map.items():
            bad = [l for l in snap.links if l.link_id in links and l.sinr_db < 8]
            if len(bad) >= 2:
                alerts.append(DownstreamAlert(
                    alert_id=str(uuid.uuid4())[:8],
                    alert_type="spectrum_conflict",
                    timestamp=snap.timestamp,
                    risk_level=RiskLevel.MODERATE,
                    affected_links=links,
                    affected_freq_hz=[freq],
                    trace=AlertTrace(
                        reason=f"频段 {freq/1e9:.2f}GHz 多链路 SINR 偏低",
                        rules_applied=["co_channel_conflict", "sinr_threshold_8db"],
                    ),
                ))
        return alerts

    def _trace(self, link: LinkState, snap: SituationalSnapshot) -> AlertTrace:
        jammer_ids = [j["id"] for j in snap.jammers]
        explained = explain_link_degradation(link.sinr_db, jammer_ids)
        rules = ["sinr_risk_classification"] + explained.get("rules_applied", [])
        if link.interference_power_dbm > -80:
            rules.append("high_interference_detected")
        if link.sinr_db < 0:
            rules.append("link_unavailable_threshold")
        return AlertTrace(
            jammer_ids=jammer_ids[:3],
            reason=explained["reason"],
            rules_applied=rules,
        )

    @staticmethod
    def _recommend_freq(link: LinkState) -> float | None:
        if link.center_freq_hz <= 0:
            return None
        # Simple recommendation: shift 200MHz away from current
        return link.center_freq_hz + 200e6

    def assess_dimensions(self, snap: SituationalSnapshot) -> dict:
        """5-dimensional risk summary."""
        links = [l for l in snap.links if l.visible]
        return {
            "link": self._dim_summary(links, "link_id"),
            "frequency": self._freq_summary(links),
            "region": {"affected_satellites": len({l.source_id for l in links if l.sinr_db < 10})},
            "satellite": self._dim_summary(links, "source_id"),
            "business": {"degraded_links_pct": sum(1 for l in links if l.sinr_db < 10) / max(len(links), 1) * 100},
        }

    @staticmethod
    def _dim_summary(links, key):
        bad = [getattr(l, key) for l in links if l.sinr_db < 10]
        return {"high_risk_count": len(bad), "entities": list(set(bad))[:10]}

    @staticmethod
    def _freq_summary(links):
        freqs = [l.center_freq_hz for l in links if l.visible and l.sinr_db < 10 and l.center_freq_hz]
        return {"high_risk_frequencies_hz": sorted(set(freqs))[:10]}
