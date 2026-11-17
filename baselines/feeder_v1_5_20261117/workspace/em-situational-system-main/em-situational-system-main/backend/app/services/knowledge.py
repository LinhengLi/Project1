"""Knowledge rules for explainability and physics validation."""

from __future__ import annotations

import json
from pathlib import Path

from app.config import settings


def load_rules() -> dict:
    path = settings.data_dir / "knowledge" / "rules_v0.json"
    if path.exists():
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return {"standards": [], "physics": [], "experience": []}


def explain_link_degradation(sinr_db: float, jammer_ids: list[str]) -> dict:
    rules = load_rules()
    applied = []
    for r in rules.get("physics", []):
        if r["id"] == "sinr_thresholds":
            applied.append(r["rule"])
    reason_parts = [f"SINR={sinr_db:.1f}dB"]
    if jammer_ids:
        reason_parts.append(f"受干扰源 {', '.join(jammer_ids[:3])} 影响")
    reason_parts.append("依据自由空间损耗与多源干扰叠加模型")
    return {
        "reason": "；".join(reason_parts),
        "rules_applied": applied,
        "standards": [s["rule"] for s in rules.get("standards", [])[:2]],
    }
