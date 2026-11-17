"""REST API routes."""

from __future__ import annotations

import asyncio
import json
from typing import AsyncGenerator

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from sse_starlette.sse import EventSourceResponse

from app.models.schemas import (
    CompletionRequest,
    ExperimentConfig,
    ImportScenarioRequest,
    PredictionRequest,
    ScenarioModeRequest,
)
from app.services.experiments import experiment_service
from app.services.scenario_manager import sim_manager

router = APIRouter(prefix="/api/v1")


@router.post("/scenario/load")
def load_scenario(req: ImportScenarioRequest):
    try:
        scenario = sim_manager.load_scenario(req.path)
        return {
            "status": "ok",
            "scenario_id": scenario.scenario_id,
            "name": scenario.name,
            "data_sources": [item.model_dump(mode="json") for item in sim_manager.get_data_sources()],
        }
    except FileNotFoundError:
        raise HTTPException(404, f"Scenario not found: {req.path}")
    except Exception as exc:
        raise HTTPException(500, str(exc))


@router.get("/scenario/current")
def current_scenario():
    if not sim_manager.scenario:
        raise HTTPException(400, "No scenario loaded")
    return sim_manager.scenario.model_dump(mode="json")


@router.get("/scenario/data-sources")
def scenario_data_sources():
    return [item.model_dump(mode="json") for item in sim_manager.get_data_sources()]


@router.get("/scenario/mode")
def get_scenario_mode():
    return sim_manager.get_mode_status().model_dump(mode="json")


@router.post("/scenario/mode")
def set_scenario_mode(req: ScenarioModeRequest):
    try:
        return sim_manager.set_mode(req.mode).model_dump(mode="json")
    except FileNotFoundError as exc:
        raise HTTPException(404, f"Scenario not found: {exc}")
    except Exception as exc:
        raise HTTPException(500, str(exc))


@router.post("/simulation/step")
def simulation_step(delta_sec: int | None = None):
    try:
        snap = sim_manager.step(delta_sec)
        return snap.model_dump(mode="json")
    except RuntimeError as exc:
        raise HTTPException(400, str(exc))


@router.get("/situational/current")
def situational_current(
    sparse: bool = False,
    observation_rate: float = 0.25,
    realtime: bool = False,
    refresh_sources: bool = False,
):
    try:
        snap = sim_manager.get_snapshot(
            sparse=sparse,
            obs_rate=observation_rate,
            realtime=realtime,
            refresh_sources=refresh_sources,
        )
        return snap.model_dump(mode="json")
    except RuntimeError as exc:
        raise HTTPException(400, str(exc))


@router.post("/situational/complete")
def situational_complete(req: CompletionRequest):
    try:
        snap = sim_manager.complete_situational(req)
        return snap.model_dump(mode="json")
    except RuntimeError as exc:
        raise HTTPException(400, str(exc))


@router.post("/situational/predict")
def situational_predict(req: PredictionRequest):
    try:
        return sim_manager.predict(req)
    except RuntimeError as exc:
        raise HTTPException(400, str(exc))


@router.get("/alerts")
def get_alerts(limit: int = 50):
    return [alert.model_dump(mode="json") for alert in sim_manager.get_alerts(limit)]


@router.get("/risk/assessment")
def risk_assessment():
    if not sim_manager.risk:
        raise HTTPException(400, "No scenario loaded")
    snap = sim_manager.get_snapshot()
    return sim_manager.risk.assess_dimensions(snap)


@router.get("/constellation/positions")
def constellation_positions(realtime: bool = False):
    return sim_manager.get_satellite_positions(realtime=realtime)


@router.get("/downstream/payload")
def downstream_payload():
    try:
        return sim_manager.export_downstream_payload()
    except RuntimeError as exc:
        raise HTTPException(400, str(exc))


@router.get("/completion/compare")
def completion_compare(observation_rate: float = 0.25):
    if not sim_manager.situational or not sim_manager.completion:
        raise HTTPException(400, "No scenario loaded")
    snap = sim_manager.get_snapshot()
    if not snap.spectrum_grid:
        raise HTTPException(400, "No spectrum grid")
    return sim_manager.completion.benchmark_methods(snap.spectrum_grid, observation_rate=observation_rate)


@router.post("/experiments")
def create_experiment(config: ExperimentConfig):
    return experiment_service.create_experiment(config).model_dump(mode="json")


@router.get("/experiments")
def list_experiments():
    return [run.model_dump(mode="json") for run in experiment_service.list_experiments()]


@router.delete("/experiments")
def clear_experiments():
    return experiment_service.clear_experiments()


@router.get("/experiments/{experiment_id}")
def get_experiment(experiment_id: str):
    try:
        return experiment_service.get_experiment(experiment_id).model_dump(mode="json")
    except KeyError:
        raise HTTPException(404, f"Experiment not found: {experiment_id}")


@router.delete("/experiments/{experiment_id}")
def delete_experiment(experiment_id: str):
    try:
        return experiment_service.delete_experiment(experiment_id)
    except KeyError:
        raise HTTPException(404, f"Experiment not found: {experiment_id}")


@router.get("/experiments/{experiment_id}/progress")
def get_experiment_progress(experiment_id: str):
    try:
        return experiment_service.get_progress(experiment_id)
    except KeyError:
        raise HTTPException(404, f"Experiment not found: {experiment_id}")


@router.post("/experiments/{experiment_id}/run")
def run_experiment(experiment_id: str):
    try:
        return experiment_service.run_experiment(experiment_id).model_dump(mode="json")
    except KeyError:
        raise HTTPException(404, f"Experiment not found: {experiment_id}")
    except Exception as exc:
        raise HTTPException(500, str(exc))


@router.post("/experiments/{experiment_id}/export")
def export_experiment(experiment_id: str, format: str = "json"):
    try:
        return experiment_service.export_experiment(experiment_id, format).model_dump(mode="json")
    except KeyError:
        raise HTTPException(404, f"Experiment not found: {experiment_id}")
    except Exception as exc:
        raise HTTPException(500, str(exc))


@router.get("/experiments/{experiment_id}/cases/{case_id}/replay")
def replay_experiment_case(experiment_id: str, case_id: str):
    try:
        return experiment_service.replay_case(experiment_id, case_id)
    except KeyError as exc:
        raise HTTPException(404, f"Replay resource not found: {exc}")


@router.get("/experiments/{experiment_id}/artifacts/{artifact_name}")
def download_experiment_artifact(experiment_id: str, artifact_name: str):
    try:
        return FileResponse(experiment_service.artifact_path(experiment_id, artifact_name))
    except KeyError:
        raise HTTPException(404, f"Experiment not found: {experiment_id}")
    except FileNotFoundError:
        raise HTTPException(404, f"Artifact not found: {artifact_name}")


async def _alert_stream() -> AsyncGenerator[dict, None]:
    last_count = 0
    while True:
        alerts = sim_manager.get_alerts(100)
        if len(alerts) > last_count:
            for alert in alerts[last_count:]:
                yield {"event": "alert", "data": json.dumps(alert.model_dump(mode="json"))}
            last_count = len(alerts)
        if sim_manager.current_time:
            yield {
                "event": "heartbeat",
                "data": json.dumps({"time": sim_manager.current_time.isoformat()}),
            }
        await asyncio.sleep(2)


@router.get("/stream/alerts")
async def stream_alerts():
    return EventSourceResponse(_alert_stream())

