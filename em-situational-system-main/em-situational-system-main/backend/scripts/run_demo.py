"""End-to-end demo script."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.scenario_manager import SimulationManager


def main():
    mgr = SimulationManager()
    scenario_path = Path(__file__).resolve().parents[2] / "data" / "scenarios" / "demo_leo_v0.json"
    print(f"Loading scenario: {scenario_path}")
    scenario = mgr.load_scenario(scenario_path)
    print(f"  Scenario: {scenario.name}")
    print(f"  Satellites: {len(mgr.satellites)}")

    print("\n--- Simulation steps ---")
    for i in range(10):
        snap = mgr.step()
        visible = [l for l in snap.links if l.visible]
        bad = [l for l in visible if l.sinr_db < 10]
        print(f"  Step {i+1}: t={snap.timestamp}, links={len(visible)}, high_risk={len(bad)}")

    print("\n--- Sparse completion ---")
    from app.models.schemas import CompletionRequest
    comp_snap = mgr.complete_situational(CompletionRequest(observation_rate=0.25, method="kriging"))
    print(f"  Method: {comp_snap.spectrum_grid.completion_method if comp_snap.spectrum_grid else 'N/A'}")

    compare = mgr.completion.compare_methods(mgr.get_snapshot().spectrum_grid)
    print("\n--- Completion comparison (25% obs) ---")
    for method, stats in compare.items():
        imp = stats.get("improvement_vs_kriging_pct", 0)
        print(f"  {method}: RMSE={stats.get('rmse', 'N/A'):.3f}, vs Kriging={imp:.1f}%")

    print("\n--- Prediction (5 min) ---")
    from app.models.schemas import PredictionRequest
    pred = mgr.predict(PredictionRequest(horizon_sec=300))
    print(f"  Confidence: {pred['overall_confidence']}")
    print(f"  High risk links: {len(pred['high_risk_links'])}")

    print("\n--- Downstream payload ---")
    payload = mgr.export_downstream_payload()
    print(json.dumps(payload, indent=2, ensure_ascii=False)[:800])

    print("\nDemo complete.")


if __name__ == "__main__":
    main()
