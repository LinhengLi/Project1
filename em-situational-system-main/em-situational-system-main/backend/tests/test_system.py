"""Test suite for EMS platform."""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.models.schemas import CompletionRequest, DataMode, ExperimentConfig
from app.services.data_source import DataSourceService
from app.services.experiments import ExperimentService
from app.services.scenario_manager import SimulationManager
from app.services.spectrum import classify_spectrum_relation, freq_overlap




def test_manager_defaults_to_online_mode():
    mgr = SimulationManager()
    assert mgr.current_mode == DataMode.ONLINE
    assert mgr.mode_paths[mgr.current_mode] == "tle_online_v0.json"


@pytest.fixture
def manager():
    mgr = SimulationManager()
    path = Path(__file__).resolve().parents[2] / "data" / "scenarios" / "demo_leo_v0.json"
    mgr.load_scenario(path)
    return mgr


def test_scenario_loads(manager):
    assert manager.scenario is not None
    assert len(manager.satellites) == 50


def test_simulation_step(manager):
    snap = manager.step()
    assert snap.timestamp is not None
    assert len(snap.links) > 0


def test_sparse_completion(manager):
    snap = manager.complete_situational(CompletionRequest(observation_rate=0.25))
    assert snap.spectrum_grid.completed


def test_freq_overlap():
    assert freq_overlap(14e9, 100e6, 14e9, 100e6) == 100e6
    assert classify_spectrum_relation(14e9, 100e6, 14e9, 100e6) == "co_channel"


def test_prediction(manager):
    for _ in range(5):
        manager.step()
    from app.models.schemas import PredictionRequest

    pred = manager.predict(PredictionRequest(horizon_sec=60))
    assert pred["horizon_sec"] == 60
    assert "link_predictions" in pred


def test_switch_data_mode(manager, monkeypatch, tmp_path):
    tle_text = "ISS\n1 25544U 98067A   24169.50000000  .00016717  00000+0  10270-3 0  9990\n2 25544  51.6410 281.2065 0004932 146.5159 300.8432 15.50000000000019\n"

    class OkResponse:
        text = tle_text

        @staticmethod
        def raise_for_status():
            return None

    monkeypatch.setattr("app.services.data_source.httpx.get", lambda *args, **kwargs: OkResponse())
    manager.data_source_service = DataSourceService(cache_dir=tmp_path)
    mode = manager.set_mode(DataMode.ONLINE)
    assert mode.mode == DataMode.ONLINE
    assert mode.scenario_path == "tle_online_v0.json"
    assert mode.data_sources
    assert mode.data_sources[0].source_type == "online_tle"

    mode = manager.set_mode(DataMode.SIMULATION)
    assert mode.mode == DataMode.SIMULATION
    assert mode.scenario_path == "demo_leo_v0.json"
    assert manager.scenario is not None
    assert manager.scenario.constellation["type"] == "walker"


def test_experiment_run_and_manual_cleanup(tmp_path):
    service = ExperimentService(storage_dir=tmp_path, enable_persistence=False)
    run = service.create_experiment(ExperimentConfig(
        name="pytest_validation",
        scenario_paths=["demo_leo_v0.json"],
        observation_rates=[0.25],
        prediction_horizons_sec=[60],
        completion_methods=["kriging", "idw"],
        simulation_steps=4,
        step_delta_sec=5,
        export_formats=["json", "csv"],
    ))
    finished = service.run_experiment(run.experiment_id)

    assert finished.total_cases == 1
    assert finished.completed_cases == 1
    assert finished.cases
    assert finished.summary.total_cases == 1
    assert finished.summary.best_completion_method in {"kriging", "idw"}
    assert all(Path(item.file_path).exists() for item in finished.exports)

    replay = service.replay_case(finished.experiment_id, finished.cases[0].case_id)
    assert replay["time_series"]
    assert replay["comparison"]

    progress = service.get_progress(finished.experiment_id)
    assert progress["completed_cases"] == 1
    assert progress["total_cases"] == 1

    result_dir = Path(finished.result_dir)
    assert result_dir.exists()
    deleted = service.delete_experiment(finished.experiment_id)
    assert deleted["deleted"] is True
    assert not result_dir.exists()
    assert service.list_experiments() == []


def test_clear_experiments(tmp_path):
    service = ExperimentService(storage_dir=tmp_path, enable_persistence=False)
    for index in range(2):
        service.create_experiment(ExperimentConfig(name=f"exp_{index}", scenario_paths=["demo_leo_v0.json"]))
    assert len(service.list_experiments()) == 2
    cleared = service.clear_experiments()
    assert cleared["deleted"] is True
    assert service.list_experiments() == []


def test_heal_stale_running_experiment(tmp_path):
    experiments_dir = Path(__file__).resolve().parents[2] / "data" / "experiments"
    candidates = sorted(experiments_dir.glob("*/run.json"))
    if not candidates:
        pytest.skip("Run an experiment locally before testing stale experiment recovery.")

    payload = json.loads(candidates[-1].read_text(encoding="utf-8"))
    experiment_id = payload["experiment_id"]
    target_dir = tmp_path / experiment_id
    target_dir.mkdir(parents=True, exist_ok=True)
    payload["result_dir"] = str(target_dir)
    payload["status"] = "running"
    payload["finished_at"] = None
    payload["exports"] = []
    (target_dir / "run.json").write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    service = ExperimentService(storage_dir=tmp_path, enable_persistence=False)
    run = service.get_experiment(experiment_id)

    assert run.status.value == "completed"
    assert run.finished_at is not None
    assert run.summary.total_cases == run.total_cases
    assert len(run.exports) == len(run.config.export_formats)
    assert {item.format for item in run.exports} == set(run.config.export_formats)


def test_online_tle_cache_fallback(tmp_path, monkeypatch):
    service = DataSourceService(cache_dir=tmp_path)
    tle_text = "ISS\n1 25544U 98067A   24169.50000000  .00016717  00000+0  10270-3 0  9990\n2 25544  51.6410 281.2065 0004932 146.5159 300.8432 15.50000000000019\n"

    class OkResponse:
        text = tle_text

        @staticmethod
        def raise_for_status():
            return None

    monkeypatch.setattr("app.services.data_source.httpx.get", lambda *args, **kwargs: OkResponse())
    first_text, first_info = service.resolve_tle("https://example.com/tle.txt", tmp_path)
    assert first_text == tle_text
    assert first_info.cache_status == "fresh"

    def fail_fetch(*args, **kwargs):
        raise RuntimeError("network unavailable")

    monkeypatch.setattr("app.services.data_source.httpx.get", fail_fetch)
    cached_text, cached_info = service.resolve_tle("https://example.com/tle.txt", tmp_path)
    assert cached_text == tle_text
    assert cached_info.cache_status == "stale_fallback"






def test_real_external_spectrum_and_jammer_import(tmp_path):
    spectrum = tmp_path / "spectrum.csv"
    spectrum.write_text(
        "timestamp,freq_hz,power_dbm\n"
        "2026-06-16T12:00:00Z,14000000000,-70.0\n"
        "2026-06-16T12:00:00Z,26000000000,-82.0\n",
        encoding="utf-8",
    )
    jammers = tmp_path / "jammers.json"
    jammers.write_text(json.dumps([
        {
            "id": "real_jam_1",
            "name": "Imported jammer",
            "source_type": "ground_fixed",
            "jamming_style": "co_channel",
            "latitude": 39.7,
            "longitude": 116.2,
            "altitude_m": 0,
            "tx_power_dbm": 42,
            "center_freq_hz": 14000000000,
            "bandwidth_hz": 50000000,
            "antenna_gain_dbi": 10,
        }
    ]), encoding="utf-8")
    scenario = tmp_path / "real_scenario.json"
    scenario.write_text(json.dumps({
        "scenario_id": "real_external_pytest",
        "name": "Real external pytest",
        "epoch": "2026-06-16T12:00:00Z",
        "time_step_sec": 10,
        "simulation_duration_sec": 60,
        "constellation": {
            "type": "walker",
            "planes": 1,
            "sats_per_plane": 2,
            "altitude_km": 550,
            "inclination_deg": 53,
        },
        "ground_stations": [{
            "id": "gs_test",
            "name": "Test GS",
            "latitude": 39.9042,
            "longitude": 116.4074,
            "altitude_m": 50,
            "antenna_gain_dbi": 35,
            "visible_elevation_deg": 0,
        }],
        "default_links": {
            "isl_center_freq_hz": 26000000000,
            "isl_bandwidth_hz": 500000000,
            "isl_tx_power_dbm": 20,
            "sgl_center_freq_hz": 14000000000,
            "sgl_bandwidth_hz": 200000000,
            "sgl_tx_power_dbm": 30,
        },
        "jammers": [],
        "external_sources": {
            "tolerance_sec": 60,
            "spectrum_observations": {"source": spectrum.name},
            "jammers": {"source": jammers.name, "mode": "append"},
        },
    }), encoding="utf-8")

    mgr = SimulationManager()
    mgr.load_scenario(scenario)
    snap = mgr.get_snapshot()

    assert len(mgr.scenario.jammers) == 1
    assert len(mgr.get_data_sources()) == 2
    assert snap.spectrum_grid.completion_method == "real_observation"
    assert sum(snap.spectrum_grid.observed_mask) == 2
    assert any(abs(power + 70.0) < 1e-6 for power in snap.spectrum_grid.power_dbm)
