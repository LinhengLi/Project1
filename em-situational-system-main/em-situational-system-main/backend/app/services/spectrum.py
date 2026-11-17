"""Spectrum resource modeling and conflict detection."""

from __future__ import annotations

from app.models.schemas import LinkConfigModel, LinkType


def freq_overlap(f1: float, bw1: float, f2: float, bw2: float) -> float:
    """Return overlap bandwidth in Hz (0 if none)."""
    low1, high1 = f1 - bw1 / 2, f1 + bw1 / 2
    low2, high2 = f2 - bw2 / 2, f2 + bw2 / 2
    overlap = min(high1, high2) - max(low1, low2)
    return max(0.0, overlap)


def classify_spectrum_relation(f1: float, bw1: float, f2: float, bw2: float) -> str:
    overlap = freq_overlap(f1, bw1, f2, bw2)
    if overlap <= 0:
        sep = abs(f1 - f2) - (bw1 + bw2) / 2
        if sep <= 0:
            return "adjacent_leakage"
        return "none"
    if abs(f1 - f2) < min(bw1, bw2) * 0.1:
        return "co_channel"
    return "partial_overlap"


class SpectrumResourceModel:
    """Track link spectrum occupancy and detect conflicts."""

    def __init__(self, links: list[LinkConfigModel]):
        self.links = links

    def occupancy_at_freq(self, freq_hz: float, bandwidth_hz: float = 1e6) -> list[str]:
        """Return link IDs occupying given frequency band."""
        occupied = []
        for link in self.links:
            if freq_overlap(link.center_freq_hz, link.bandwidth_hz, freq_hz, bandwidth_hz) > 0:
                occupied.append(link.id)
        return occupied

    def detect_conflicts(self) -> list[dict]:
        conflicts = []
        for i, l1 in enumerate(self.links):
            for l2 in self.links[i + 1:]:
                rel = classify_spectrum_relation(
                    l1.center_freq_hz, l1.bandwidth_hz,
                    l2.center_freq_hz, l2.bandwidth_hz,
                )
                if rel != "none":
                    conflicts.append({
                        "link_a": l1.id,
                        "link_b": l2.id,
                        "relation": rel,
                        "overlap_hz": freq_overlap(
                            l1.center_freq_hz, l1.bandwidth_hz,
                            l2.center_freq_hz, l2.bandwidth_hz,
                        ),
                    })
        return conflicts

    def build_spectrum_grid(self, freq_start_hz: float, freq_end_hz: float, num_bins: int,
                            power_fn) -> dict:
        """Build discretized spectrum occupancy grid."""
        import numpy as np
        bins = np.linspace(freq_start_hz, freq_end_hz, num_bins)
        power = [power_fn(f) for f in bins]
        return {"freq_bins_hz": bins.tolist(), "power_dbm": power}
