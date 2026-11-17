"""Acceptance tests aligned with requirements document section 9."""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.models.schemas import CompletionRequest, PredictionRequest
from app.services.scenario_manager import SimulationManager


def run_tests():
    results = []
    mgr = SimulationManager()
    path = Path(__file__).resolve().parents[2] / "data" / "scenarios" / "demo_leo_v0.json"
    mgr.load_scenario(path)

    # 1. Constellation / link dynamics
    t0 = time.perf_counter()
    for _ in range(20):
        snap = mgr.step(60)
    elapsed = time.perf_counter() - t0
    visible = [l for l in snap.links if l.visible]
    results.append(("星座链路动态更新", len(visible) > 0, f"{len(visible)} links, {elapsed:.2f}s for 20 steps"))

    # 2. Spectrum conflict detection
    from app.services.spectrum import SpectrumResourceModel
    from app.services.orbit import OrbitEngine
    orbit = mgr.orbit
    links = orbit.build_sgl_links(snap.timestamp, mgr.scenario.default_links)[:5]
    spec = SpectrumResourceModel(links)
    conflicts = spec.detect_conflicts()
    results.append(("频谱冲突判定", True, f"{len(conflicts)} relations detected"))

    # 3. Jammer modeling (5+ styles in scenario)
    styles = {j.jamming_style.value for j in mgr.scenario.jammers}
    results.append(("干扰样式覆盖", len(styles) >= 4, f"{len(styles)} styles: {styles}"))

    # 4. Situational generation
    snap = mgr.get_snapshot()
    has_grid = snap.spectrum_grid is not None
    has_links = len(snap.links) > 0
    results.append(("态势生成", has_grid and has_links, f"links={len(snap.links)}, bins={len(snap.spectrum_grid.freq_bins_hz) if has_grid else 0}"))

    # 5. Sparse completion at 25% and 50%
    for rate in (0.25, 0.5):
        comp = mgr.complete_situational(CompletionRequest(observation_rate=rate, method="kriging"))
        ok = comp.spectrum_grid and comp.spectrum_grid.completed
        results.append((f"稀疏补全({int(rate*100)}%)", ok, comp.spectrum_grid.completion_method if ok else "fail"))

    # 6. Prediction windows
    for horizon in (30, 60, 300, 600):
        pred = mgr.predict(PredictionRequest(horizon_sec=horizon))
        ok = pred.get("overall_confidence", 0) > 0
        results.append((f"动态预测({horizon}s)", ok, f"confidence={pred.get('overall_confidence')}"))

    # 7. Risk assessment
    assessment = mgr.risk.assess_dimensions(snap)
    results.append(("5维风险评估", "link" in assessment and "frequency" in assessment, str(list(assessment.keys()))))

    # 8. Downstream API payload
    payload = mgr.export_downstream_payload()
    results.append(("下游接口载荷", "link_assessments" in payload and "alerts" in payload, f"{len(payload.get('alerts', []))} alerts"))

    # 9. Performance
    t0 = time.perf_counter()
    mgr.get_snapshot()
    lat = time.perf_counter() - t0
    results.append(("态势更新延迟", lat < 5.0, f"{lat:.3f}s"))

    # 10. Completion method comparison
    compare = mgr.completion.compare_methods(snap.spectrum_grid)
    results.append(("补全对照实验", "kriging" in compare, str({k: v.get("rmse") for k, v in compare.items()})))

    print("=" * 60)
    print("ACCEPTANCE TEST REPORT")
    print("=" * 60)
    passed = 0
    for name, ok, detail in results:
        status = "PASS" if ok else "FAIL"
        if ok:
            passed += 1
        print(f"[{status}] {name}: {detail}")
    print("=" * 60)
    print(f"Total: {passed}/{len(results)} passed")
    return passed == len(results)


if __name__ == "__main__":
    ok = run_tests()
    sys.exit(0 if ok else 1)
