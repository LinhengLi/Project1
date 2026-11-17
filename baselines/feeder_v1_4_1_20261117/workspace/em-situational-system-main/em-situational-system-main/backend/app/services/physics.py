"""Physics consistency validation rules."""

from __future__ import annotations

import math


RULES = [
    {
        "id": "fspl_monotonic",
        "description": "路径损耗应随距离增大而增大",
    },
    {
        "id": "power_conservation",
        "description": "接收功率不应超过发射功率+增益",
    },
    {
        "id": "sinr_bounds",
        "description": "SINR 应在物理合理范围内",
    },
]


def validate_fspl_monotonic(distances_m: list[float], fspl_values: list[float]) -> tuple[bool, str]:
    for i in range(1, len(distances_m)):
        if distances_m[i] > distances_m[i - 1] and fspl_values[i] < fspl_values[i - 1] - 0.1:
            return False, f"FSPL decreases at distance {distances_m[i]}m"
    return True, ""


def validate_link_budget(tx_dbm: float, rx_dbm: float, max_gain_db: float = 60) -> tuple[bool, str]:
    if rx_dbm > tx_dbm + max_gain_db:
        return False, f"Rx power {rx_dbm} exceeds tx+gain {tx_dbm + max_gain_db}"
    return True, ""


def validate_sinr(sinr_db: float) -> tuple[bool, str]:
    if sinr_db > 60:
        return False, f"SINR {sinr_db} dB unrealistically high"
    if sinr_db < -50:
        return False, f"SINR {sinr_db} dB below physical floor"
    return True, ""


class PhysicsValidator:
    """Apply physics and knowledge constraints to situational outputs."""

    def validate_link(self, link_state: dict) -> list[str]:
        violations = []
        ok, msg = validate_sinr(link_state.get("sinr_db", 0))
        if not ok:
            violations.append(msg)
        ok, msg = validate_link_budget(
            link_state.get("tx_power_dbm", 0),
            link_state.get("rx_power_dbm", -999),
        )
        if not ok:
            violations.append(msg)
        return violations

    def validate_spectrum_completion(
        self, freq_bins: list[float], power_dbm: list[float]
    ) -> tuple[float, list[str]]:
        """Return confidence penalty and violation messages."""
        violations = []
        penalty = 0.0
        for i, p in enumerate(power_dbm):
            if p > 30:
                violations.append(f"Bin {freq_bins[i]/1e9:.2f}GHz power {p} dBm too high")
                penalty += 0.2
            if p < -150:
                violations.append(f"Bin {freq_bins[i]/1e9:.2f}GHz power unrealistically low")
                penalty += 0.1
        return min(penalty, 0.9), violations
