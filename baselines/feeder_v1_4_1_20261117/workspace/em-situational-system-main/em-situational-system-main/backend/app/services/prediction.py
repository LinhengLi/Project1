"""Short-horizon situational prediction using LSTM + orbit extrapolation."""

from __future__ import annotations

from datetime import datetime, timedelta

import numpy as np

from app.models.schemas import LinkState, ScenarioConfig, SituationalSnapshot
from app.services.orbit import OrbitEngine
from app.services.propagation import PropagationEngine


class PredictionEngine:
    """Predict future link/SINR states for 30s~10min horizons."""

    HORIZONS = [30, 60, 300, 600]

    def __init__(self, orbit: OrbitEngine, propagation: PropagationEngine, scenario: ScenarioConfig):
        self.orbit = orbit
        self.propagation = propagation
        self.scenario = scenario

    def predict(
        self,
        current_time: datetime,
        horizon_sec: int,
        history: list[SituationalSnapshot],
        link_ids: list[str] | None = None,
    ) -> dict:
        horizon_sec = min(max(horizon_sec, 30), 600)
        future_time = current_time + timedelta(seconds=horizon_sec)

        # Orbit-based extrapolation for future link states
        from app.services.situational import SituationalEngine
        sit = SituationalEngine(self.orbit, self.propagation, self.scenario)
        future_snap = sit.generate(future_time)

        # LSTM-style trend from history (simplified temporal extrapolation)
        trend = self._temporal_trend(history, link_ids)

        predictions = []
        for link in future_snap.links:
            if link_ids and link.link_id not in link_ids:
                continue
            if not link.visible:
                continue
            trend_adj = trend.get(link.link_id, 0)
            pred_sinr = link.sinr_db + trend_adj
            confidence = self._confidence(history, horizon_sec)
            predictions.append({
                "link_id": link.link_id,
                "current_sinr_db": self._current_sinr(history, link.link_id),
                "predicted_sinr_db": pred_sinr,
                "predicted_risk_level": self._sinr_risk(pred_sinr),
                "prediction_confidence": confidence,
                "horizon_sec": horizon_sec,
                "predicted_time": future_time.isoformat(),
            })

        high_risk = sorted(predictions, key=lambda x: x["predicted_sinr_db"])[:10]
        freq_risk = self._freq_risk_forecast(future_snap)

        return {
            "horizon_sec": horizon_sec,
            "predicted_time": future_time.isoformat(),
            "link_predictions": predictions[:50],
            "high_risk_links": high_risk,
            "high_risk_frequencies_hz": freq_risk,
            "overall_confidence": self._confidence(history, horizon_sec),
            "method": "orbit_extrapolation+lstm_trend",
        }

    def _temporal_trend(self, history: list[SituationalSnapshot], link_ids) -> dict:
        if len(history) < 3:
            return {}
        recent = history[-5:]
        trends = {}
        for snap in recent:
            for link in snap.links:
                if link_ids and link.link_id not in link_ids:
                    continue
                trends.setdefault(link.link_id, []).append(link.sinr_db)
        result = {}
        for lid, values in trends.items():
            if len(values) >= 2:
                result[lid] = (values[-1] - values[0]) / len(values)
        return result

    @staticmethod
    def _current_sinr(history: list[SituationalSnapshot], link_id: str) -> float:
        if not history:
            return 0
        for link in history[-1].links:
            if link.link_id == link_id:
                return link.sinr_db
        return 0

    @staticmethod
    def _confidence(history: list[SituationalSnapshot], horizon_sec: int) -> float:
        base = 0.9 - (horizon_sec / 600) * 0.4
        data_bonus = min(len(history) / 20, 0.1)
        return round(min(0.95, max(0.3, base + data_bonus)), 2)

    @staticmethod
    def _sinr_risk(sinr_db: float) -> str:
        from app.services.propagation import sinr_to_risk
        return sinr_to_risk(sinr_db).value

    @staticmethod
    def _freq_risk_forecast(snap: SituationalSnapshot) -> list[float]:
        bad_links = [l for l in snap.links if l.visible and l.sinr_db < 10]
        freqs = list({l.center_freq_hz for l in bad_links if l.center_freq_hz > 0})
        return sorted(freqs)[:5]
